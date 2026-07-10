import json
import logging
import asyncio
import uuid
import datetime as dt
from typing import Any, Dict, List, Optional, AsyncGenerator

import asyncpg

from app.schemas.ai import AIChatRequest, ChatMessage
from app.ai.gateway.ai_gateway import AIGateway
from app.ai.agents.workspace_assistant import WorkspaceAssistantAgent
from app.ai.context.workspace_context import WorkspaceContextBuilder
from app.ai.schemas.planning import (
    ExecutionContext, ExecutionPlan, ExecutionResult,
    ExecutionStatus,
)
from app.ai.orchestration.intent_router import IntentRouter, IntentType
from app.ai.orchestration.planner import Planner
from app.ai.orchestration.validator import PlanValidator
from app.ai.orchestration.executor import Executor
from app.ai.orchestration.composer import ResponseComposer
from app.ai.orchestration.conversational import conversation_registry
from app.ai.orchestration.clarification_router import ClarificationRouter
from app.ai.orchestration.errors import ErrorMessageFactory
from app.ai.orchestration.state_machine import ExecutionStateMachine
from app.ai.orchestration.idempotency import idempotency_store
from app.ai.orchestration.timeouts import timeout_policy
from app.ai.exceptions import (
    ExecutionTimeoutError, FailureCategory, MissingInformationError,
)
from app.ai.telemetry.context import TraceContext, _request_state
from app.ai.telemetry.tracer import RequestTracer
from app.ai.config_budgets import performance_budgets
from app.ai.prompts.registry import PromptRegistry
from app.ai.services.rate_limiter import check_rate_limit
from app.ai.services.sse import (
    sse_event, sse_message_start, sse_message_chunk, sse_message_end, sse_error,
)
from app.services.board_service import BoardService
from app.services.task_service import TaskService
from app.services.user_service import UserService
from app.services.comment_service import CommentService

logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES = 20


class AIService:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn
        self.gateway = AIGateway()

    # ------------------------------------------------------------------
    # Context helpers
    # ------------------------------------------------------------------

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

        db_context["Current Date & Time"] = dt.datetime.now().isoformat()
        return db_context

    @staticmethod
    def _build_planner_input(messages: List[ChatMessage]) -> tuple[str, str]:
        """Return (user_input, planner_input) with conversation history for context."""
        if not messages:
            return "", ""

        user_input = messages[-1].content

        if len(messages) > 1:
            history_slice = messages[-(MAX_HISTORY_MESSAGES + 1):-1]
            history_lines = []
            for m in history_slice:
                role_name = "User" if m.role == "user" else "Assistant"
                content = m.content
                if m.role == "assistant" and len(content) > 300:
                    content = content[:300] + "..."
                history_lines.append(f"{role_name}: {content}")

            history_str = "\n".join(history_lines)
            planner_input = f"Conversation History:\n{history_str}\n\nCurrent Request:\n{user_input}"
        else:
            planner_input = user_input

        return user_input, planner_input

    @staticmethod
    def _extract_history_state(messages: List[ChatMessage]) -> tuple[Optional[dict], list, dict]:
        """Scan message history for pending clarifications and recently resolved entities.

        Returns (pending_plan_data, missing_fields, recent_entities).
        """
        pending_plan_data = None
        missing_fields: list = []
        recent_entities: dict = {}

        if not messages:
            return pending_plan_data, missing_fields, recent_entities

        for msg in reversed(messages[-10:]):
            events = getattr(msg, "metadata", {}).get("events", []) if getattr(msg, "metadata", None) else []
            for evt in events:
                if evt.get("type") == "entity_resolved":
                    etype = evt.get("entity_type")
                    if etype and etype not in recent_entities:
                        recent_entities[etype] = evt

        last_msg = messages[-1]
        if last_msg.role == "assistant":
            events = getattr(last_msg, "metadata", {}).get("events", []) if getattr(last_msg, "metadata", None) else []
            for evt in events:
                if evt.get("type") == "pending_clarification":
                    pending_plan_data = evt.get("plan")
                    missing_fields = evt.get("missing_fields", [])

        return pending_plan_data, missing_fields, recent_entities

    # ------------------------------------------------------------------
    # SSE stream flows
    # ------------------------------------------------------------------

    async def _handle_conversational(
        self, user_input: str, request: AIChatRequest, exec_context: ExecutionContext
    ) -> AsyncGenerator[str, None]:
        """Handle CONVERSATIONAL / KNOWLEDGE intents."""
        yield sse_message_start(exec_context.execution_id)

        template_response = conversation_registry.get_response(user_input)
        if template_response:
            yield sse_message_chunk(template_response)
            yield sse_message_end()
            return

        system_prompt = PromptRegistry.render_prompt(
            agent_name="workspace_assistant",
            prompt_name="chat",
            context={"workspace_context": exec_context.workspace_context_str},
            version="v1",
        )

        chat_messages = [{"role": "system", "content": system_prompt}] + [m.model_dump() for m in request.messages]

        stream_gen = self.gateway.stream_prompt(
            messages=chat_messages,
            org_ai_enabled=True,
            user_has_permission=exec_context.current_user.get("role") in ["SUPER_ADMIN", "MANAGER"],
            workflow_id="conversational",
            request_id=exec_context.request_id,
            organization_id=exec_context.organization_id,
            user_id=str(exec_context.current_user.get("id")),
        )

        async for chunk in stream_gen:
            if chunk and "content" in chunk:
                yield sse_message_chunk(chunk["content"])
                await asyncio.sleep(0)

        yield sse_message_end()

    async def _resolve_clarification(
        self, user_input: str, pending_plan_data: dict, missing_fields: list, exec_context: ExecutionContext
    ) -> AsyncGenerator[str, None]:
        """Resolve a pending clarification and yield the appropriate SSE events.

        Yields SSE events. If the generator ends without yielding a 'planning_completed'
        event, the caller should fall through to normal planning.
        """
        c_router = ClarificationRouter(self.gateway)
        decision = await c_router.resolve(
            user_input,
            ExecutionPlan(**pending_plan_data),
            missing_fields,
            request_id=exec_context.request_id,
            organization_id=exec_context.organization_id,
            user_id=str(exec_context.current_user.get("id")),
            user_has_permission=exec_context.current_user.get("role") in ["SUPER_ADMIN", "MANAGER"]
        )

        if decision.decision == "CANCEL":
            yield sse_message_start(exec_context.execution_id)
            yield sse_message_chunk("Okay, cancelled.")
            yield sse_message_end()
            return

        if decision.decision == "RESUME" and decision.updated_plan:
            plan = ExecutionPlan(**decision.updated_plan)
            ExecutionStateMachine.validate_transition(exec_context.current_state, ExecutionStatus.PLANNING)
            exec_context.current_state = ExecutionStatus.PLANNING
            yield sse_event("planning_started", timestamp=0)
            yield sse_event("planning_completed", plan=plan.model_dump(), timestamp=0)
            # Signal to caller: plan is ready, skip normal planning
            yield sse_event("_internal_plan_ready", plan=plan.model_dump())

    async def _run_planning(
        self, user_input: str, planner_input: str, exec_context: ExecutionContext, agent: WorkspaceAssistantAgent
    ) -> AsyncGenerator[str, None]:
        """Run the planner and yield SSE events. Final event carries the plan."""
        ExecutionStateMachine.validate_transition(exec_context.current_state, ExecutionStatus.PLANNING)
        exec_context.current_state = ExecutionStatus.PLANNING
        yield sse_event("planning_started", timestamp=0)

        planner = Planner(self.gateway)
        try:
            plan = await asyncio.wait_for(
                planner.create_plan(user_input, exec_context, agent.available_tools, planner_input),
                timeout=timeout_policy.planner_timeout_sec,
            )
        except asyncio.TimeoutError:
            raise ExecutionTimeoutError("Planning timed out", stage="PLANNING")

        if getattr(plan, "clarification_needed", None):
            yield sse_event("execution_cancelled")
            yield sse_message_start(exec_context.execution_id)
            yield sse_message_chunk(plan.clarification_needed)
            yield sse_message_end()
            exec_context.current_state = ExecutionStatus.CANCELLED
            return

        if getattr(plan, "confidence_score", 1.0) < 0.7:
            yield sse_error("I am not entirely sure how to proceed with that request. Could you clarify or provide more details?")
            exec_context.current_state = ExecutionStatus.FAILED
            return

        yield sse_event("planning_completed", plan=plan.model_dump(), timestamp=0)
        yield sse_event("_internal_plan_ready", plan=plan.model_dump())

    def _build_services(self, recent_entities: dict) -> dict:
        return {
            "board_service": BoardService(self.conn),
            "task_service": TaskService(self.conn),
            "user_service": UserService(self.conn),
            "comment_service": CommentService(self.conn),
            "recent_entities": recent_entities,
        }

    async def _run_execution(
        self, plan: ExecutionPlan, exec_context: ExecutionContext, agent: WorkspaceAssistantAgent,
        services: dict, skip_confirmation: bool
    ) -> AsyncGenerator[str, None]:
        """Validate, execute, compose — the full action pipeline."""
        # --- Validate ---
        ExecutionStateMachine.validate_transition(exec_context.current_state, ExecutionStatus.VALIDATING)
        exec_context.current_state = ExecutionStatus.VALIDATING

        try:
            PlanValidator.validate(plan, exec_context, agent.available_tools)
        except MissingInformationError as e:
            yield sse_event("pending_clarification", plan=e.plan.model_dump() if e.plan else None, missing_fields=e.missing_fields)
            yield sse_event("execution_cancelled")
            yield sse_message_start(exec_context.execution_id)
            yield sse_message_chunk(str(e))
            yield sse_message_end()
            exec_context.current_state = ExecutionStatus.CANCELLED
            return

        # --- Execute ---
        ExecutionStateMachine.validate_transition(exec_context.current_state, ExecutionStatus.EXECUTING)
        exec_context.current_state = ExecutionStatus.EXECUTING
        executor = Executor(services, agent.available_tools)
        execution_result: Optional[ExecutionResult] = None

        try:
            async for event_string in executor.execute(plan, exec_context, skip_confirmation):
                try:
                    event_data = json.loads(event_string.replace("data: ", "").strip())
                    if event_data.get("type") == "execution_result":
                        execution_result = ExecutionResult(**event_data.get("result"))
                        continue
                except Exception:
                    pass
                yield event_string
                await asyncio.sleep(0)
        except asyncio.TimeoutError:
            raise ExecutionTimeoutError("Overall execution timed out", stage="EXECUTING")

        if not execution_result:
            return

        ExecutionStateMachine.validate_transition(exec_context.current_state, execution_result.status)
        exec_context.current_state = execution_result.status

        # --- Emit entity_resolved events ---
        if execution_result.status in [ExecutionStatus.COMPLETED, ExecutionStatus.PARTIALLY_COMPLETED]:
            for step_res in execution_result.step_results:
                if step_res.status == "success" and step_res.result:
                    result_data = step_res.result
                    if "task" in result_data and isinstance(result_data["task"], dict) and "id" in result_data["task"]:
                        yield sse_event("entity_resolved", entity_type="task", entity_id=result_data["task"]["id"])
                    elif "board" in result_data and isinstance(result_data["board"], dict) and "id" in result_data["board"]:
                        yield sse_event("entity_resolved", entity_type="board", entity_id=result_data["board"]["id"])
                    elif "board_id" in result_data:
                        yield sse_event("entity_resolved", entity_type="board", entity_id=result_data["board_id"])

            # --- Compose response ---
            composer = ResponseComposer(self.gateway)
            async for event_string in composer.compose(execution_result, exec_context):
                yield event_string
                await asyncio.sleep(0)

        elif execution_result.status == ExecutionStatus.FAILED:
            yield sse_message_start(exec_context.execution_id)
            error_details = [sr.error for sr in execution_result.step_results if sr.error]
            error_msg = error_details[0] if error_details else "An error occurred while processing your request."
            yield sse_message_chunk(error_msg)
            yield sse_message_end()

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def chat_stream(self, request: AIChatRequest, current_user: dict, request_id: str) -> AsyncGenerator[str, None]:
        execution_id = str(uuid.uuid4())
        tracer = RequestTracer(request_id=request_id, execution_id=execution_id)
        tracer.start()

        agent = WorkspaceAssistantAgent()

        idemp_key = f"{request.conversation_id}_{request_id}"
        if not idempotency_store.acquire(idemp_key):
            yield sse_error(
                ErrorMessageFactory._templates[FailureCategory.VALIDATION_ERROR],
                details="Duplicate request.",
            )
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
                current_state=ExecutionStatus.CREATED,
            )
            exec_context.timeout_metadata = timeout_policy.model_dump()
            exec_context.execution_id = tracer.execution_id

            workspace_ctx_dict = await self._build_full_context(current_user, request.ui_context)
            exec_context.workspace_context_str = json.dumps(workspace_ctx_dict)

            user_input, planner_input = self._build_planner_input(request.messages)
            pending_plan_data, missing_fields, recent_entities = self._extract_history_state(request.messages)

            # --- Confirmed plan (user clicked confirm) ---
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
                    llm_context=planner_input,
                    user_has_permission = exec_context.current_user.get("role") == "SUPER_ADMIN" or exec_context.current_user.get("role") == "MANAGER"
                )


            # --- Conversational / Knowledge ---
            if intent in [IntentType.CONVERSATIONAL, IntentType.KNOWLEDGE]:
                async for evt in self._handle_conversational(user_input, request, exec_context):
                    yield evt
                return

            # --- Workspace action flow ---
            plan = None
            skip_confirmation = False

            if request.confirmed_plan:
                plan = ExecutionPlan(**request.confirmed_plan)
                skip_confirmation = True
            else:
                # Clarification resolution
                if pending_plan_data and missing_fields:
                    plan_ready = False
                    async for evt in self._resolve_clarification(user_input, pending_plan_data, missing_fields, exec_context):
                        if '"_internal_plan_ready"' in evt:
                            event_data = json.loads(evt.replace("data: ", "").strip())
                            plan = ExecutionPlan(**event_data["plan"])
                            plan_ready = True
                            continue
                        yield evt
                    if not plan_ready and plan is None:
                        # CANCEL was emitted or NEW_INTENT — if cancel, we already yielded; if new intent, fall through
                        if exec_context.current_state != ExecutionStatus.PLANNING:
                            return

                # Normal planning
                if plan is None:
                    async for evt in self._run_planning(user_input, planner_input, exec_context, agent):
                        if '"_internal_plan_ready"' in evt:
                            event_data = json.loads(evt.replace("data: ", "").strip())
                            plan = ExecutionPlan(**event_data["plan"])
                            continue
                        yield evt
                    if plan is None:
                        return

            # --- Execute ---
            services = self._build_services(recent_entities)
            async for evt in self._run_execution(plan, exec_context, agent, services, skip_confirmation):
                yield evt

        except asyncio.CancelledError:
            if exec_context:
                exec_context.is_cancelled = True
                exec_context.current_state = ExecutionStatus.CANCELLED
            tracer.end(Exception("Request was cancelled"))
            yield sse_event("execution_cancelled")
            raise
        except Exception as e:
            user_msg = ErrorMessageFactory.get_user_message(e)
            if exec_context:
                exec_context.current_state = ExecutionStatus.FAILED
            tracer.end(e)
            logger.error(f"Error in chat_stream: {str(e)}", exc_info=True)
            yield sse_error(user_msg)
        finally:
            idempotency_store.release(idemp_key)
            try:
                tracer.end()
                state = _request_state.get()
                if state:
                    llm_calls = state.get("total_llm_calls", 0)
                    tokens = state.get("total_tokens", 0)
                    duration = state.get("duration_ms", 0)

                    if llm_calls > performance_budgets.max_total_llm_calls:
                        logger.warning(f"[PERFORMANCE BUDGET] LLM Calls: {llm_calls} > {performance_budgets.max_total_llm_calls}. Request: {request_id}")
                    if tokens > performance_budgets.max_prompt_tokens:
                        logger.warning(f"[PERFORMANCE BUDGET] Tokens: {tokens} > {performance_budgets.max_prompt_tokens}. Request: {request_id}")
                    if duration > performance_budgets.max_execution_time_ms:
                        logger.warning(f"[PERFORMANCE BUDGET] Duration: {duration}ms > {performance_budgets.max_execution_time_ms}ms. Request: {request_id}")
            except Exception as e:
                logger.error(f"Error checking performance budgets: {str(e)}")
