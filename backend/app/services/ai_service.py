import json
import logging
import asyncio
import os
from typing import Any, Dict, List, Optional, AsyncGenerator
from datetime import datetime
import asyncpg
from fastapi import HTTPException

from app.schemas.ai import AIChatRequest, ChatMessage
from app.ai.gateway.ai_gateway import AIGateway
from app.ai.agents.workspace_assistant import WorkspaceAssistantAgent
from app.ai.context.workspace_context import WorkspaceContextBuilder
from app.ai.tools.registry import tool_registry
from app.ai.schemas.planning import ExecutionContext, ExecutionPlan, ExecutionStatus
from app.ai.orchestration.router import IntentRouter, IntentType
from app.ai.orchestration.planner import Planner
from app.ai.orchestration.validator import PlanValidator
from app.ai.orchestration.executor import Executor
from app.ai.orchestration.composer import ResponseComposer

logger = logging.getLogger(__name__)

# Limits users to 15 requests per minute to match Gemini Free Tier
_RATE_LIMIT_STORE: Dict[int, List[datetime]] = {}
RATE_LIMIT_REQUESTS = int(os.environ.get("RATE_LIMIT_REQUESTS", 15))
RATE_LIMIT_WINDOW = 60  # seconds

# Maximum conversation history messages to include for planner context
MAX_HISTORY_MESSAGES = 20


def check_rate_limit(user_id: int):
    now = datetime.utcnow()
    timestamps = _RATE_LIMIT_STORE.get(user_id, [])
    timestamps = [ts for ts in timestamps if (now - ts).total_seconds() < RATE_LIMIT_WINDOW]
    
    if len(timestamps) >= RATE_LIMIT_REQUESTS:
        raise HTTPException(status_code=429, detail="AI request rate limit exceeded. Please try again later.")
    
    timestamps.append(now)
    _RATE_LIMIT_STORE[user_id] = timestamps


class AIService:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn
        self.gateway = AIGateway()
        
    async def _build_full_context(self, current_user: dict, ui_context) -> Dict[str, Any]:
        context_builder = WorkspaceContextBuilder(self.conn)
        
        board_id = None
        if ui_context:
            if hasattr(ui_context, "board_id"):
                board_id = ui_context.board_id
            elif isinstance(ui_context, dict):
                board_id = ui_context.get("board_id")
                
        db_context = await context_builder.build(current_user=current_user, board_id=board_id)
        
        if ui_context:
            if hasattr(ui_context, "model_dump"):
                db_context["ui_context"] = ui_context.model_dump()
            elif isinstance(ui_context, dict):
                db_context["ui_context"] = ui_context
                
        import datetime
        db_context["Current Date & Time"] = datetime.datetime.now().isoformat()
            
        return db_context

    def _build_planner_input(self, messages: List[ChatMessage]) -> tuple[str, str]:
        """Build user_input and planner_input from message list.
        
        Returns (user_input, planner_input) where planner_input includes
        conversation history for context resolution.
        """
        if not messages:
            return "", ""
        
        user_input = messages[-1].content
        
        if len(messages) > 1:
            # Include up to MAX_HISTORY_MESSAGES for context
            history_slice = messages[-(MAX_HISTORY_MESSAGES + 1):-1]
            history_lines = []
            for m in history_slice:
                role_name = "User" if m.role == "user" else "Assistant"
                # Truncate long assistant responses to save tokens
                content = m.content
                if m.role == "assistant" and len(content) > 300:
                    content = content[:300] + "..."
                history_lines.append(f"{role_name}: {content}")
            
            history_str = "\n".join(history_lines)
            planner_input = f"Conversation History:\n{history_str}\n\nCurrent Request:\n{user_input}"
        else:
            planner_input = user_input
        
        return user_input, planner_input

    async def chat_stream(self, request: AIChatRequest, current_user: dict, request_id: str) -> AsyncGenerator[str, None]:
        from app.ai.telemetry.context import TraceContext
        from app.ai.telemetry.tracer import RequestTracer
        from app.ai.orchestration.errors import ErrorMessageFactory
        from app.ai.orchestration.state_machine import ExecutionStateMachine
        from app.ai.orchestration.idempotency import idempotency_store
        from app.ai.orchestration.timeouts import timeout_policy
        from app.ai.exceptions import ExecutionTimeoutError, UserCancellationError, FailureCategory
        
        import uuid
        execution_id = str(uuid.uuid4())
        tracer = RequestTracer(
            request_id=request_id,
            execution_id=execution_id
        )
        tracer.start()
        
        agent = WorkspaceAssistantAgent()
        
        # Idempotency check
        idemp_key = f"{request.conversation_id}_{request_id}"
        if not idempotency_store.acquire(idemp_key):
            error_msg = ErrorMessageFactory._templates[FailureCategory.VALIDATION_ERROR]
            yield f"data: {json.dumps({'v': '1.0', 'type': 'error', 'error': error_msg, 'details': 'Duplicate request.'})}\n\n"
            tracer.end()
            return
            
        exec_context = None
        try:
            check_rate_limit(current_user.get("id"))
            
            exec_context = ExecutionContext(
                current_user=current_user,
                conversation_id=request.conversation_id,
                request_id=request_id,
                organization_id=str(current_user.get("organization_id")),
                idempotency_key=idemp_key,
                current_state=ExecutionStatus.CREATED
            )
            exec_context.timeout_metadata = timeout_policy.model_dump()
            exec_context.execution_id = tracer.execution_id
            
            # Build workspace context
            workspace_ctx_dict = await self._build_full_context(current_user, request.ui_context)
            exec_context.workspace_context_str = json.dumps(workspace_ctx_dict)
            
            # Build planner input with full conversation history
            user_input, planner_input = self._build_planner_input(request.messages)
            
            if request.confirmed_plan:
                plan = ExecutionPlan(**request.confirmed_plan)
                skip_confirmation = True
                intent = IntentType.WORKSPACE_ACTION
                ExecutionStateMachine.validate_transition(exec_context.current_state, ExecutionStatus.WAITING_FOR_CONFIRMATION)
                exec_context.current_state = ExecutionStatus.WAITING_FOR_CONFIRMATION
            else:
                router = IntentRouter(self.gateway)
                intent = await router.classify(
                    user_input=user_input, 
                    request_id=exec_context.request_id, 
                    organization_id=exec_context.organization_id, 
                    user_id=str(exec_context.current_user.get("id")),
                    llm_context=planner_input
                )
                
            if intent in [IntentType.CONVERSATIONAL, IntentType.KNOWLEDGE]:
                yield f"data: {json.dumps({'v': '1.0', 'type': 'assistant_message_start', 'execution_id': exec_context.execution_id})}\n\n"
                
                from app.ai.orchestration.conversational import conversation_registry
                template_response = conversation_registry.get_response(user_input)
                if template_response:
                    yield f"data: {json.dumps({'v': '1.0', 'type': 'assistant_message_chunk', 'content': template_response})}\n\n"
                    yield f"data: {json.dumps({'v': '1.0', 'type': 'assistant_message_end'})}\n\n"
                    return
                
                from app.ai.prompts.registry import PromptRegistry
                system_prompt = PromptRegistry.render_prompt(
                    agent_name="workspace_assistant",
                    prompt_name="chat",
                    context={"workspace_context": exec_context.workspace_context_str},
                    version="v1"
                )
                
                chat_messages = [{"role": "system", "content": system_prompt}] + [m.model_dump() for m in request.messages]
                
                stream_gen = self.gateway.stream_prompt(
                    messages=chat_messages,
                    org_ai_enabled=True,
                    user_has_permission=True,
                    workflow_id="conversational",
                    request_id=exec_context.request_id,
                    organization_id=exec_context.organization_id,
                    user_id=str(exec_context.current_user.get("id"))
                )
                
                async for chunk in stream_gen:
                    if chunk and "content" in chunk:
                        yield f"data: {json.dumps({'v': '1.0', 'type': 'assistant_message_chunk', 'content': chunk['content']})}\n\n"
                        await asyncio.sleep(0)
                        
                yield f"data: {json.dumps({'v': '1.0', 'type': 'assistant_message_end'})}\n\n"
                return
                
            # WORKSPACE_ACTION flow
            if not request.confirmed_plan:
                ExecutionStateMachine.validate_transition(exec_context.current_state, ExecutionStatus.PLANNING)
                exec_context.current_state = ExecutionStatus.PLANNING
                yield f"data: {json.dumps({'v': '1.0', 'type': 'planning_started', 'timestamp': 0})}\n\n"
                
                planner = Planner(self.gateway)
                try:
                    plan = await asyncio.wait_for(
                        planner.create_plan(user_input, exec_context, agent.available_tools, planner_input),
                        timeout=timeout_policy.planner_timeout_sec
                    )
                except asyncio.TimeoutError:
                    raise ExecutionTimeoutError("Planning timed out", stage="PLANNING")
                
                if getattr(plan, "clarification_needed", None):
                    yield f"data: {json.dumps({'v': '1.0', 'type': 'execution_cancelled'})}\n\n"
                    yield f"data: {json.dumps({'v': '1.0', 'type': 'assistant_message_start', 'execution_id': exec_context.execution_id})}\n\n"
                    yield f"data: {json.dumps({'v': '1.0', 'type': 'assistant_message_chunk', 'content': plan.clarification_needed})}\n\n"
                    yield f"data: {json.dumps({'v': '1.0', 'type': 'assistant_message_end'})}\n\n"
                    exec_context.current_state = ExecutionStatus.CANCELLED
                    return
                    
                if getattr(plan, "confidence_score", 1.0) < 0.7:
                    yield f"data: {json.dumps({'v': '1.0', 'type': 'error', 'error': 'I am not entirely sure how to proceed with that request. Could you clarify or provide more details?'})}\n\n"
                    exec_context.current_state = ExecutionStatus.FAILED
                    return
                
                yield f"data: {json.dumps({'v': '1.0', 'type': 'planning_completed', 'plan': plan.model_dump(), 'timestamp': 0})}\n\n"
                skip_confirmation = False
                
            ExecutionStateMachine.validate_transition(exec_context.current_state, ExecutionStatus.VALIDATING)
            exec_context.current_state = ExecutionStatus.VALIDATING
            PlanValidator.validate(plan, exec_context, agent.available_tools)
            
            from app.services.board_service import BoardService
            from app.services.task_service import TaskService
            from app.services.user_service import UserService
            from app.services.comment_service import CommentService
            
            services = {
                "board_service": BoardService(self.conn),
                "task_service": TaskService(self.conn),
                "user_service": UserService(self.conn),
                "comment_service": CommentService(self.conn)
            }
            
            ExecutionStateMachine.validate_transition(exec_context.current_state, ExecutionStatus.EXECUTING)
            exec_context.current_state = ExecutionStatus.EXECUTING
            executor = Executor(services, agent.available_tools)
            execution_result = None
            
            try:
                async def run_executor():
                    nonlocal execution_result
                    async for event_string in executor.execute(plan, exec_context, skip_confirmation):
                        try:
                            event_data = json.loads(event_string.replace('data: ', '').strip())
                            if event_data.get('type') == 'execution_result':
                                from app.ai.schemas.planning import ExecutionResult
                                execution_result = ExecutionResult(**event_data.get('result'))
                                continue
                        except:
                            pass
                        yield event_string
                        await asyncio.sleep(0)
                
                # No outer transaction — let individual service methods handle atomicity
                async for evt in run_executor():
                    yield evt
                    
            except asyncio.TimeoutError:
                raise ExecutionTimeoutError("Overall execution timed out", stage="EXECUTING")
                
            if execution_result:
                ExecutionStateMachine.validate_transition(exec_context.current_state, execution_result.status)
                exec_context.current_state = execution_result.status
                if execution_result.status in [ExecutionStatus.COMPLETED, ExecutionStatus.PARTIALLY_COMPLETED]:
                    composer = ResponseComposer(self.gateway)
                    async for event_string in composer.compose(execution_result, exec_context):
                        yield event_string
                        await asyncio.sleep(0)
                elif execution_result.status == ExecutionStatus.FAILED:
                    yield f"data: {json.dumps({'v': '1.0', 'type': 'assistant_message_start', 'execution_id': exec_context.execution_id})}\n\n"
                    error_details = []
                    for sr in execution_result.step_results:
                        if sr.error:
                            error_details.append(sr.error)
                    error_msg = error_details[0] if error_details else "An error occurred while processing your request."
                    yield f"data: {json.dumps({'v': '1.0', 'type': 'assistant_message_chunk', 'content': error_msg})}\n\n"
                    yield f"data: {json.dumps({'v': '1.0', 'type': 'assistant_message_end'})}\n\n"
                
        except asyncio.CancelledError:
            if exec_context:
                exec_context.is_cancelled = True
                exec_context.current_state = ExecutionStatus.CANCELLED
            tracer.end(Exception("Request was cancelled"))
            yield f"data: {json.dumps({'v': '1.0', 'type': 'execution_cancelled'})}\n\n"
            raise
        except Exception as e:
            from app.ai.orchestration.errors import ErrorMessageFactory
            user_msg = ErrorMessageFactory.get_user_message(e)
            if exec_context:
                exec_context.current_state = ExecutionStatus.FAILED
            tracer.end(e)
            logger.error(f"Error in chat_stream: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'v': '1.0', 'type': 'error', 'error': user_msg})}\n\n"
        finally:
            idempotency_store.release(idemp_key)
            try:
                tracer.end()
                from app.ai.telemetry.context import _request_state
                from app.ai.config_budgets import performance_budgets
                state = _request_state.get()
                if state:
                    llm_calls = state.get("total_llm_calls", 0)
                    tokens = state.get("total_tokens", 0)
                    duration = state.get("duration_ms", 0)
                    
                    if llm_calls > performance_budgets.max_total_llm_calls:
                        logger.warning(f"[PERFORMANCE BUDGET OVERSHOOT] LLM Calls: {llm_calls} > {performance_budgets.max_total_llm_calls}. Request: {request_id}")
                    if tokens > performance_budgets.max_prompt_tokens:
                        logger.warning(f"[PERFORMANCE BUDGET OVERSHOOT] Tokens: {tokens} > {performance_budgets.max_prompt_tokens}. Request: {request_id}")
                    if duration > performance_budgets.max_execution_time_ms:
                        logger.warning(f"[PERFORMANCE BUDGET OVERSHOOT] Duration: {duration}ms > {performance_budgets.max_execution_time_ms}ms. Request: {request_id}")
            except Exception as e:
                logger.error(f"Error checking performance budgets: {str(e)}")
