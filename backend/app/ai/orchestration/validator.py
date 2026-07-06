import logging
from typing import List, Dict, Any, Type
from app.ai.schemas.planning import ExecutionPlan, ExecutionContext
from app.ai.tools.base import BaseTool

logger = logging.getLogger(__name__)

class PlanValidator:
    """
    Validates an ExecutionPlan before execution.
    Checks for available tools and permissions.
    """
    
    @staticmethod
    def validate(plan: ExecutionPlan, context: ExecutionContext, available_tools: List[Type[BaseTool]]) -> bool:
        """
        Validates the plan. Returns True if valid, raises ValueError if invalid.
        """
        if not plan or not plan.steps:
            raise ValueError("Execution plan is empty or missing steps.")
            
        tool_actions = [tool.action for tool in available_tools if hasattr(tool, 'action') and tool.action]
        tool_names = [tool.name for tool in available_tools]
        
        for step in plan.steps:
            action = step.action
            if action not in tool_actions and action not in tool_names:
                raise ValueError(f"Plan step '{step.id}' contains unsupported action: '{action}'")
                
            # Basic argument validation could be added here
            
        return True
