import json
import logging
import time
import asyncio
from typing import List, Dict, Any, Type, AsyncGenerator
from app.ai.schemas.planning import (
    ExecutionPlan, ExecutionContext, ExecutionResult, ExecutionStatus, StepStatus, RiskLevel, StepExecutionResult
)
from app.ai.tools.base import BaseTool
from app.ai.orchestration.recovery import RecoveryPolicy, RecoveryAction
from app.ai.exceptions import ToolExecutionError, UserCancellationError

logger = logging.getLogger(__name__)

class Executor:
    """
    Executes an ExecutionPlan step-by-step.
    Handles partial failures, cancellations, and state machine boundaries safely.
    """
    def __init__(self, services: Dict[str, Any], available_tools: List[Type[BaseTool]]):
        self.services = services
        self.available_tools = available_tools
        self.action_to_tool = {}
        for tool_cls in available_tools:
            if hasattr(tool_cls, 'action') and tool_cls.action:
                self.action_to_tool[tool_cls.action] = tool_cls
            if hasattr(tool_cls, 'name') and tool_cls.name:
                self.action_to_tool[tool_cls.name] = tool_cls

    def _create_event(self, context: ExecutionContext, event_type: str, payload: Dict[str, Any]) -> str:
        event = {
            "v": "1.0",
            "execution_id": context.execution_id,
            "type": event_type,
            "timestamp": int(time.time() * 1000),
            **payload
        }
        return f"data: {json.dumps(event)}\n\n"

    async def execute(self, plan: ExecutionPlan, context: ExecutionContext, skip_confirmation: bool = False) -> AsyncGenerator[str, ExecutionResult]:
        start_time = time.time()
        
        from app.ai.telemetry.context import Span, TraceContext
        from app.ai.telemetry.events import EventType
        from app.ai.telemetry.bus import telemetry_bus
        
        with Span("Execute Plan", "Executor") as exec_span:
            exec_span.metadata["goal"] = plan.goal
            exec_span.metadata["total_steps"] = len(plan.steps)
            
            result = ExecutionResult(
                execution_id=context.execution_id,
                status=ExecutionStatus.EXECUTING,
                summary=f"Executing goal: {plan.goal}"
            )
            
            yield self._create_event(context, "execution_started", {"goal": plan.goal, "total_steps": len(plan.steps), "plan": plan.model_dump()})
            
            skip_remaining = False
            
            for i, step in enumerate(plan.steps):
                if context.is_cancelled:
                    result.status = ExecutionStatus.CANCELLED
                    break
                    
                if skip_remaining:
                    result.status = ExecutionStatus.PARTIALLY_COMPLETED
                    yield self._create_event(context, "step_skipped", {"step_id": step.id, "reason": "Previous step failed."})
                    continue

                with Span(f"Step: {step.action}", "ToolExecution") as tool_span:
                    tool_span.metadata["step_id"] = step.id
                    
                    tool_cls = self.action_to_tool.get(step.action)
                    if not tool_cls:
                        yield self._create_event(context, "error", {"step_id": step.id, "message": f"Action {step.action} not found."})
                        result.status = ExecutionStatus.PARTIALLY_COMPLETED if i > 0 else ExecutionStatus.FAILED
                        result.failed_steps.append(step.id)
                        tool_span.metadata["status"] = "failed"
                        tool_span.metadata["error"] = "Action not found"
                        skip_remaining = True
                        continue
                        
                    risk = tool_cls.risk_level
                    if risk in [RiskLevel.MEDIUM, RiskLevel.HIGH] and not skip_confirmation:
                        yield self._create_event(context, "confirmation_required", {
                            "step_id": step.id, 
                            "plan": plan.model_dump(),
                            "reason": f"Action '{step.action}' requires confirmation."
                        })
                        result.status = ExecutionStatus.WAITING_FOR_CONFIRMATION
                        yield self._create_event(context, "execution_result", {"result": result.model_dump()})
                        tool_span.metadata["status"] = "confirmation_required"
                        return
                        
                    yield self._create_event(context, "step_started", {"step_id": step.id, "description": step.description})
                    
                    tool_instance = tool_cls()
                    try:
                        validated_args = tool_instance.input_schema(**step.arguments)
                        
                        cache_key = f"{step.action}_{json.dumps(step.arguments, sort_keys=True)}"
                        if cache_key in context.tool_cache:
                            tool_output = context.tool_cache[cache_key]
                        else:
                            # Apply tool timeout if defined
                            tool_timeout = context.timeout_metadata.get('tool_timeout_sec', 30.0)
                            
                            tool_output = await asyncio.wait_for(
                                tool_instance.run(validated_args, context.current_user, self.services),
                                timeout=tool_timeout
                            )
                            context.tool_cache[cache_key] = tool_output
                        
                        step_result = StepExecutionResult(
                            step_id=step.id,
                            tool_name=tool_cls.name,
                            action=step.action,
                            status=StepStatus.COMPLETED,
                            output=tool_output
                        )
                        result.step_results.append(step_result)
                        
                        yield self._create_event(context, "step_completed", {"step_id": step.id, "result": "Success"})
                        result.completed_steps.append(step.id)
                        
                        result.tool_metrics[tool_cls.name] = result.tool_metrics.get(tool_cls.name, 0) + 1
                        TraceContext.increment_metric("tools_executed")
                        
                        yield self._create_event(context, "content", {"content": f"\n\n*(Completed: {step.description})*\n"})
                        
                    except asyncio.TimeoutError:
                        logger.error(f"Execution timed out at step {step.id}")
                        yield self._create_event(context, "execution_failed", {"step_id": step.id, "error": "Step timed out."})
                        result.status = ExecutionStatus.PARTIALLY_COMPLETED if i > 0 else ExecutionStatus.FAILED
                        result.failed_steps.append(step.id)
                        
                        step_result = StepExecutionResult(
                            step_id=step.id,
                            tool_name=tool_cls.name,
                            action=step.action,
                            status=StepStatus.FAILED,
                            error="Step timed out."
                        )
                        result.step_results.append(step_result)
                        
                        # Create compensation hook metadata
                        context.recovery_metadata["compensation_hooks"] = context.recovery_metadata.get("compensation_hooks", [])
                        context.recovery_metadata["compensation_hooks"].append({"step_id": step.id, "action": step.action, "reason": "timeout"})
                        
                        skip_remaining = True
                    except asyncio.CancelledError:
                        result.status = ExecutionStatus.CANCELLED
                        raise
                    except Exception as e:
                        logger.error(f"Execution failed at step {step.id}: {e}")
                        
                        # Determine recovery via policy
                        action = RecoveryPolicy.determine_action_for_error(e)
                        
                        yield self._create_event(context, "execution_failed", {"step_id": step.id, "error": str(e)})
                        
                        if i > 0:
                            result.status = ExecutionStatus.PARTIALLY_COMPLETED
                        else:
                            result.status = ExecutionStatus.FAILED
                            
                        result.failed_steps.append(step.id)
                        tool_span.metadata["status"] = "failed"
                        tool_span.metadata["error"] = str(e)
                        
                        step_result = StepExecutionResult(
                            step_id=step.id,
                            tool_name=tool_cls.name,
                            action=step.action,
                            status=StepStatus.FAILED,
                            error=str(e)
                        )
                        result.step_results.append(step_result)
                        
                        context.recovery_metadata["compensation_hooks"] = context.recovery_metadata.get("compensation_hooks", [])
                        context.recovery_metadata["compensation_hooks"].append({"step_id": step.id, "action": step.action, "reason": "failure", "error": str(e)})
                        
                        if action == RecoveryAction.FAIL or action == RecoveryAction.PARTIAL:
                            skip_remaining = True
                        else:
                            raise e
                    
            if result.status == ExecutionStatus.EXECUTING:
                result.status = ExecutionStatus.COMPLETED
                yield self._create_event(context, "execution_completed", {"summary": result.summary})
                
            result.duration_ms = int((time.time() - start_time) * 1000)
            yield self._create_event(context, "execution_result", {"result": result.model_dump()})
