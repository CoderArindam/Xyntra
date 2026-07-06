import json
import logging
import time
from typing import List, Dict, Any, Type, AsyncGenerator
from app.ai.schemas.planning import (
    ExecutionPlan, ExecutionContext, ExecutionResult, ExecutionStatus, StepStatus, RiskLevel
)
from app.ai.tools.base import BaseTool

logger = logging.getLogger(__name__)

class Executor:
    """
    Executes an ExecutionPlan step-by-step.
    Does not use the LLM; only executes validated tool actions.
    Yields SSE events to stream progress.
    """
    def __init__(self, services: Dict[str, Any], available_tools: List[Type[BaseTool]]):
        self.services = services
        self.available_tools = available_tools
        # Pre-build a map of abstract actions to concrete tools
        self.action_to_tool = {}
        for tool_cls in available_tools:
            if hasattr(tool_cls, 'action') and tool_cls.action:
                self.action_to_tool[tool_cls.action] = tool_cls
            else:
                self.action_to_tool[tool_cls.name] = tool_cls

    def _create_event(self, context: ExecutionContext, event_type: str, payload: Dict[str, Any]) -> str:
        """Helper to create versioned SSE events."""
        event = {
            "v": "1.0",
            "execution_id": context.execution_id,
            "type": event_type,
            "timestamp": int(time.time() * 1000),
            **payload
        }
        return f"data: {json.dumps(event)}\n\n"

    async def execute(self, plan: ExecutionPlan, context: ExecutionContext, skip_confirmation: bool = False) -> AsyncGenerator[str, ExecutionResult]:
        """
        Iterates over the plan steps.
        Yields progress strings in the format of SSE data.
        Returns the final ExecutionResult.
        """
        start_time = time.time()
        
        result = ExecutionResult(
            execution_id=context.execution_id,
            status=ExecutionStatus.RUNNING,
            summary=f"Executing goal: {plan.goal}"
        )
        
        yield self._create_event(context, "execution_started", {"goal": plan.goal, "total_steps": len(plan.steps), "plan": plan.model_dump()})
        
        for step in plan.steps:
            tool_cls = self.action_to_tool.get(step.action)
            if not tool_cls:
                yield self._create_event(context, "error", {"step_id": step.id, "message": f"Action {step.action} not found."})
                result.status = ExecutionStatus.FAILED
                result.failed_steps.append(step.id)
                break
                
            risk = tool_cls.risk_level
            if risk in [RiskLevel.MEDIUM, RiskLevel.HIGH] and not skip_confirmation:
                # Halt execution for confirmation
                yield self._create_event(context, "confirmation_required", {
                    "step_id": step.id, 
                    "plan": plan.model_dump(),
                    "reason": f"Action '{step.action}' requires confirmation."
                })
                result.status = ExecutionStatus.CONFIRMATION_REQUIRED
                # Important: return result when doing a proper generator isn't easy in Python if yielding, 
                # but AsyncGenerator allows returning a value if handled carefully.
                # Actually, in async generator, return value raises StopAsyncIteration(result), which might be tricky to catch.
                # Let's just yield the result as a final event or set it.
                yield self._create_event(context, "execution_result", {"result": result.model_dump()})
                return
                
            yield self._create_event(context, "step_started", {"step_id": step.id, "description": step.description})
            
            tool_instance = tool_cls()
            try:
                # Execute the tool
                # In the future, arguments could be mapped from previous step outputs
                validated_args = tool_instance.input_schema(**step.arguments)
                tool_output = await tool_instance.run(validated_args, context.current_user, self.services)
                
                yield self._create_event(context, "step_completed", {"step_id": step.id, "result": "Success"})
                result.completed_steps.append(step.id)
                
                # Track tool metrics
                result.tool_metrics[tool_cls.name] = result.tool_metrics.get(tool_cls.name, 0) + 1
                
                # Render content if we want it in standard stream
                yield self._create_event(context, "content", {"content": f"\n\n*(Completed: {step.description})*\n"})
                
            except Exception as e:
                logger.error(f"Execution failed at step {step.id}: {e}")
                yield self._create_event(context, "execution_failed", {"step_id": step.id, "error": str(e)})
                result.status = ExecutionStatus.FAILED
                result.failed_steps.append(step.id)
                break
                
        if result.status == ExecutionStatus.RUNNING:
            result.status = ExecutionStatus.COMPLETED
            yield self._create_event(context, "execution_completed", {"summary": result.summary})
            
        result.duration_ms = int((time.time() - start_time) * 1000)
        yield self._create_event(context, "execution_result", {"result": result.model_dump()})
