import json
from typing import List, Dict, Any, Type
from app.ai.schemas.planning import ExecutionPlan, ExecutionContext
from app.ai.tools.base import BaseTool
from app.ai.gateway.ai_gateway import AIGateway
from app.ai.prompts.registry import PromptRegistry

class Planner:
    """
    Responsible for understanding intent and generating an ExecutionPlan.
    Never executes tools itself.
    """
    def __init__(self, gateway: AIGateway):
        self.gateway = gateway
        
    async def create_plan(self, user_input: str, context: ExecutionContext, available_tools: List[Type[BaseTool]]) -> ExecutionPlan:
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
                "current_user": f"{context.current_user.get('first_name')} {context.current_user.get('last_name')}",
                "organization_id": context.organization_id
            },
            version="v1"
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        
        try:
            plan = self.gateway.execute_prompt(
                messages=messages,
                response_schema=ExecutionPlan,
                org_ai_enabled=True,
                user_has_permission=True,
                workflow_id="planning",
                request_id=context.request_id,
                organization_id=context.organization_id,
                user_id=str(context.current_user.get("id"))
            )
            
            # Since execute_prompt validates against response_schema, it returns an ExecutionPlan
            if isinstance(plan, ExecutionPlan):
                return plan
            else:
                raise ValueError("Expected ExecutionPlan, got string.")
                
        except Exception as e:
            raise ValueError(f"Failed to parse execution plan: {str(e)}")
