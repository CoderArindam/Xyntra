import json
from typing import List, Dict, Any, Type
from app.ai.schemas.planning import ExecutionPlan, ExecutionContext
from app.ai.tools.base import BaseTool
from app.ai.gateway.ai_gateway import AIGateway
from app.ai.prompts.registry import PromptRegistry
from app.ai.exceptions import AIError

class Planner:
    """
    Responsible for understanding intent and generating an ExecutionPlan.
    Never executes tools itself.
    """
    def __init__(self, gateway: AIGateway):
        self.gateway = gateway
        
    async def create_plan(self, user_input: str, context: ExecutionContext, available_tools: List[Type[BaseTool]], llm_context: str = None) -> ExecutionPlan:
        from app.ai.telemetry.context import Span
        from app.ai.orchestration.fast_actions import fast_action_registry
        
        with Span("Create Plan", "Planner") as span:
            # Stage 1: Fast Plan
            fast_action = fast_action_registry.find_match(user_input)
            if fast_action:
                plan = fast_action.create_plan(user_input, available_tools)
                if plan:
                    span.metadata["method"] = "fast_plan"
                    span.metadata["steps_generated"] = len(plan.steps)
                    return plan
                    
            span.metadata["method"] = "llm"
            
            # Build available actions for the planner prompt
            actions_desc = []
            for tool in available_tools:
                if hasattr(tool, 'action') and tool.action:
                    actions_desc.append(f"- {tool.action}: {tool.description} (Risk: {tool.risk_level.value})")
                else:
                    actions_desc.append(f"- {tool.name}: {tool.description} (Risk: {tool.risk_level.value})")
                    
            actions_str = "\n".join(actions_desc)
            
            system_prompt = PromptRegistry.render_prompt(
                agent_name="workspace_assistant",
                prompt_name="planner",
                context={
                    "available_actions": actions_str,
                    "workspace_context": context.workspace_context_str
                },
                version="v1"
            )
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": llm_context if llm_context else user_input}
            ]
            
            span.metadata["available_tools_count"] = len(available_tools)
            
            try:
                plan = await self.gateway.execute_prompt(
                    messages=messages,
                    response_schema=ExecutionPlan,
                    org_ai_enabled=True,
                    user_has_permission=context.current_user.get("role") in ["SUPER_ADMIN", "MANAGER"],
                    workflow_id="planning",
                    request_id=context.request_id,
                    organization_id=context.organization_id,
                    user_id=str(context.current_user.get("id"))
                )
                
                # Since execute_prompt validates against response_schema, it returns an ExecutionPlan
                if isinstance(plan, ExecutionPlan):
                    span.metadata["steps_generated"] = len(plan.steps)
                    return plan
                else:
                    raise ValueError("Expected ExecutionPlan, got string.")
                    
            except Exception as e:
                if isinstance(e, AIError):
                    raise
                raise ValueError(f"Failed to parse execution plan: {str(e)}")
