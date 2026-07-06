import json
import logging
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime
import asyncpg
from fastapi import HTTPException

from app.schemas.ai import AIChatRequest, ChatMessage
from app.ai.gateway.ai_gateway import AIGateway
from app.ai.agents.workspace_assistant import WorkspaceAssistantAgent
from app.ai.context.workspace_context import WorkspaceContextBuilder
from app.ai.tools.registry import tool_registry

logger = logging.getLogger(__name__)

# Basic in-memory rate limiter for Phase 3.1
# Limits users to 15 requests per minute to match Gemini Free Tier
_RATE_LIMIT_STORE: Dict[int, List[datetime]] = {}
RATE_LIMIT_REQUESTS = 15
RATE_LIMIT_WINDOW = 60 # seconds

def check_rate_limit(user_id: int):
    now = datetime.utcnow()
    timestamps = _RATE_LIMIT_STORE.get(user_id, [])
    
    # Filter timestamps within the window
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
        # Merge DB context with UI context
        context_builder = WorkspaceContextBuilder(self.conn)
        board_id = ui_context.board_id if ui_context else None
        db_context = await context_builder.build(current_user=current_user, board_id=board_id)
        
        if ui_context:
            db_context["ui_context"] = ui_context.model_dump()
            
        return db_context

    async def chat_stream(self, request: AIChatRequest, current_user: dict, request_id: str):
        # 1. Rate Limiting
        check_rate_limit(current_user["id"])
        
        # 2. Build Context
        context = await self._build_full_context(current_user, request.ui_context)
        
        # 3. Setup Agent
        agent = WorkspaceAssistantAgent()
        
        # 4. Convert history to what Gateway expects
        # For this phase, we append the new history after building system messages
        last_message = request.messages[-1].content if request.messages else ""
        
        agent_messages = agent.build_messages(user_input=last_message, context=context)
        
        # Prepend history (excluding the last message as it's already in agent_messages)
        # Actually, agent.build_messages gives [system, user_input]. 
        # If there's history, we should insert it between system and user_input.
        
        system_msg = agent_messages[0]
        history = [{"role": m.role, "content": m.content} for m in request.messages[:-1]]
        current_msg = agent_messages[1]
        
        final_messages = [system_msg] + history + [current_msg]
        
        services_dict = {
            "task_service": None, # Should be injected or created if needed
            # For simplicity, we can pass self.conn to tools or instantiate services
        }
        from app.services.task_service import TaskService
        services_dict["task_service"] = TaskService(self.conn)

        # Convert Agent Tools to Gemini compatible dicts if needed
        # In this phase, we mock tool execution or implement a basic loop.
        # Actually, let's implement the loop.
        tools = []
        for tool_cls in agent.available_tools:
            tools.append({
                "type": "function",
                "function": {
                    "name": tool_cls.name,
                    "description": tool_cls.description,
                    "parameters": tool_cls.input_schema.model_json_schema()
                }
            })
        org_id = current_user.get("organization_id")
        
        try:
            from app.ai.schemas.planning import ExecutionContext, ExecutionPlan, ExecutionStatus
            from app.ai.orchestration.router import IntentRouter, IntentType
            from app.ai.orchestration.planner import Planner
            from app.ai.orchestration.validator import PlanValidator
            from app.ai.orchestration.executor import Executor
            from app.ai.orchestration.composer import ResponseComposer
            
            # Setup Services for Executor
            from app.services.board_service import BoardService
            from app.services.task_service import TaskService
            from app.services.user_service import UserService
            
            services = {
                "board_service": BoardService(self.conn),
                "task_service": TaskService(self.conn),
                "user_service": UserService(self.conn)
            }
            
            # Create ExecutionContext
            exec_context = ExecutionContext(
                current_user=current_user,
                conversation_id=request.conversation_id,
                request_id=request_id,
                organization_id=str(org_id) if org_id else None
            )
            
            user_input = request.messages[-1].content if request.messages else ""
            
            if request.confirmed_plan:
                plan = ExecutionPlan(**request.confirmed_plan)
                skip_confirmation = True
                intent = IntentType.WORKSPACE_ACTION
            else:
                # 1. Route Intent
                router = IntentRouter(self.gateway)
                intent = await router.classify(
                    user_input=user_input, 
                    request_id=exec_context.request_id, 
                    organization_id=exec_context.organization_id, 
                    user_id=str(exec_context.current_user.get("id"))
                )
                
            if intent in [IntentType.CONVERSATIONAL, IntentType.KNOWLEDGE]:
                # Stream conversational reply directly
                yield f"data: {json.dumps({'v': '1.0', 'type': 'assistant_message_start', 'execution_id': exec_context.execution_id})}\n\n"
                
                # Fetch chat system prompt
                from app.ai.prompts.registry import PromptRegistry
                system_prompt = PromptRegistry.render_prompt(
                    agent_name="workspace_assistant",
                    prompt_name="chat",
                    context={
                        "current_user": json.dumps(exec_context.current_user)
                    },
                    version="v1"
                )
                
                chat_messages = [{"role": "system", "content": system_prompt}] + [m.model_dump() for m in request.messages]
                
                # We reuse the gateway's streaming
                stream_gen = self.gateway.stream_prompt(
                    messages=chat_messages,
                    org_ai_enabled=True,
                    user_has_permission=True,
                    workflow_id="conversational",
                    request_id=exec_context.request_id,
                    organization_id=exec_context.organization_id,
                    user_id=str(exec_context.current_user.get("id"))
                )
                
                for chunk in stream_gen:
                    if chunk and "content" in chunk:
                        yield f"data: {json.dumps({'v': '1.0', 'type': 'assistant_message_chunk', 'content': chunk['content']})}\n\n"
                        await asyncio.sleep(0)
                        
                yield f"data: {json.dumps({'v': '1.0', 'type': 'assistant_message_end'})}\n\n"
                return
                
            # Otherwise WORKSPACE_ACTION flow
            if not request.confirmed_plan:
                yield f"data: {json.dumps({'v': '1.0', 'type': 'planning_started', 'timestamp': 0})}\n\n"
                
                planner = Planner(self.gateway)
                plan = await planner.create_plan(user_input, exec_context, agent.available_tools)
                
                yield f"data: {json.dumps({'v': '1.0', 'type': 'planning_completed', 'plan': plan.model_dump(), 'timestamp': 0})}\n\n"
                skip_confirmation = False
                
            # Validate plan
            PlanValidator.validate(plan, exec_context, agent.available_tools)
            
            # Execute plan
            executor = Executor(services, agent.available_tools)
            execution_result = None
            async for event_string in executor.execute(plan, exec_context, skip_confirmation):
                # We need to capture the ExecutionResult which is yielded as a special event
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
                
            if execution_result and execution_result.status == ExecutionStatus.COMPLETED:
                composer = ResponseComposer(self.gateway)
                async for event_string in composer.compose(execution_result, exec_context):
                    yield event_string
                    await asyncio.sleep(0)
                
        except asyncio.CancelledError:
            logger.info(f"AI Streaming Cancelled by client for request {request_id}")
            yield f"data: {json.dumps({'v': '1.0', 'type': 'execution_cancelled'})}\n\n"
            raise
            
        except Exception as e:
            logger.error(f"Error in chat_stream: {str(e)}")
            error_data = json.dumps({"v": "1.0", "type": "error", "error": str(e)})
            yield f"data: {error_data}\n\n"
