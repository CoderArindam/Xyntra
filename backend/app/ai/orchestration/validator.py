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
    },
    "update_profile": {
        "first_name": "What should your new first name be?",
        "last_name": "What should your new last name be?"
    },
    "update_appearance": {
        "theme": "Would you like Light, Dark, or System theme?",
        "accent_color": "Which accent color would you like? (Blue, Indigo, Emerald, Rose, Amber)",
        "sidebar_theme": "Would you like the sidebar Default, Tinted, or Dark?",
        "sidebar_collapsed": "Would you like the sidebar Expanded or Collapsed?"
    }
}

ROLES_ADMIN_MANAGER = ["SUPER_ADMIN", "MANAGER"]
ROLES_ALL = ["SUPER_ADMIN", "MANAGER", "MEMBER"]

# Per-action permission map
ACTION_REQUIRED_ROLES: Dict[str, List[str]] = {
    # Task Management
    "create_task": ROLES_ADMIN_MANAGER,
    "update_task": ROLES_ADMIN_MANAGER,
    "delete_task": ROLES_ADMIN_MANAGER,
    "move_task": ROLES_ADMIN_MANAGER,
    "reassign_task": ROLES_ADMIN_MANAGER,
    
    # Board / Project Management
    "create_board": ROLES_ADMIN_MANAGER,
    "archive_board": ROLES_ADMIN_MANAGER,
    "delete_board": ROLES_ADMIN_MANAGER,
    "update_board_settings": ROLES_ADMIN_MANAGER,

    # Self-scoped Account & Preference Management
    "update_profile": ROLES_ALL,
    "update_own_profile": ROLES_ALL,
    "get_my_profile": ROLES_ALL,
    "update_appearance": ROLES_ALL,
    "update_preferences": ROLES_ALL,
    "get_my_appearance": ROLES_ALL,

    # Read-only Queries & Comments
    "list_boards": ROLES_ALL,
    "list_projects": ROLES_ALL,
    "list_tasks": ROLES_ALL,
    "get_task": ROLES_ALL,
    "get_task_details": ROLES_ALL,
    "get_workspace_users": ROLES_ALL,
    "get_users": ROLES_ALL,
    "get_board_summary": ROLES_ALL,
    "add_comment": ROLES_ALL,
    "get_comments": ROLES_ALL,
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
            
            user_role = (context.current_user.get("role") or "MEMBER").upper()

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
                        
                # Server-side Action Authorization / Role Gate
                required_roles = getattr(tool_cls, 'required_roles', None) if tool_cls else None
                if required_roles is None:
                    required_roles = ACTION_REQUIRED_ROLES.get(action, ROLES_ALL)

                if user_role not in [r.upper() for r in required_roles]:
                    from app.ai.exceptions import PermissionError
                    raise PermissionError(
                        f"You do not have permission to perform action '{action}'. "
                        f"Only {', '.join(sorted(required_roles))} can perform task and project management actions."
                    )
                        
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
