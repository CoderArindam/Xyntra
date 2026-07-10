import logging
from typing import List, Dict, Any, Type
from app.ai.schemas.planning import ExecutionPlan, ExecutionContext
from app.ai.tools.base import BaseTool

logger = logging.getLogger(__name__)

# Natural questions for missing fields
MISSING_FIELD_QUESTIONS = {
    "create_task": {
        "title": "What would you like to call the task?",
        "board_name": "Which project or board should I create this in?"
    },
    "update_task": {
        "new_name": "What should the new name be?",
        "task_name": "Which task did you want to update?"
    },
    "create_board": {
        "name": "What should the project be called?"
    },
    "add_comment": {
        "content": "What comment would you like to add?",
        "task_name": "Which task are you adding a comment to?"
    }
}

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
        from app.ai.telemetry.context import Span
        with Span("Validate Plan", "PlanValidator") as span:
            if not plan or not plan.steps:
                raise ValueError("Execution plan is empty or missing steps.")
                
            tool_actions = [tool.action for tool in available_tools if hasattr(tool, 'action') and tool.action]
            tool_names = [tool.name for tool in available_tools]
            
            for step in plan.steps:
                action = step.action
                if action not in tool_actions and action not in tool_names:
                    raise ValueError(f"Plan step '{step.id}' contains unsupported action: '{action}'")
                    
                # Schema validation at Planner/Tool boundary
                tool_cls = None
                for tool in available_tools:
                    if tool.name == action or getattr(tool, 'action', None) == action:
                        tool_cls = tool
                        break
                        
                if tool_cls and hasattr(tool_cls, 'input_schema') and tool_cls.input_schema:
                    try:
                        tool_cls.input_schema(**step.arguments)
                    except Exception as e:
                        # Attempt to check if it's a Pydantic ValidationError
                        if hasattr(e, 'errors') and callable(e.errors):
                            missing_fields = [err["loc"][0] for err in e.errors() if err.get("type") == "missing"]
                            if missing_fields:
                                from app.ai.exceptions import MissingInformationError
                                missing_field = missing_fields[0]
                                
                                # Try to find a natural question
                                action_qs = MISSING_FIELD_QUESTIONS.get(action, {})
                                question = action_qs.get(missing_field)
                                
                                if not question:
                                    # Fallback
                                    friendly_field = missing_field.replace('_', ' ').capitalize()
                                    question = f"What should the {friendly_field} be?"
                                
                                raise MissingInformationError(
                                    question,
                                    plan=plan,
                                    missing_fields=missing_fields
                                )
                        # Not missing information, so it's a planner/schema mismatch or invalid plan
                        raise ValueError(f"Invalid execution plan arguments for '{action}': {e}")
            
            span.metadata["steps_validated"] = len(plan.steps)
            return True
