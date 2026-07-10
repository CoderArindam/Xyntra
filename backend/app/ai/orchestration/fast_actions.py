import re
from typing import Dict, Any, Callable, List, Type
from pydantic import BaseModel
from app.ai.schemas.planning import ExecutionPlan, PlanStep


class FastAction(BaseModel):
    action_name: str
    patterns: List[str]
    _compiled_patterns: List[re.Pattern] = []

    def __init__(self, **data):
        super().__init__(**data)
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.patterns]

    def match(self, text: str) -> bool:
        return any(p.match(text) for p in self._compiled_patterns)
        
    def extract_params(self, text: str) -> Dict[str, Any]:
        if self.action_name == "update_appearance":
            t = text.lower()
            if "dark" in t: return {"theme": "dark"}
            if "light" in t: return {"theme": "light"}
            if "system" in t: return {"theme": "system"}
            if "collapse" in t: return {"sidebar_collapsed": True}
            if "expand" in t: return {"sidebar_collapsed": False}
            if "reset" in t or "restore" in t: return {"reset_defaults": True}
            
        for p in self._compiled_patterns:
            match = p.match(text)
            if match:
                groups = match.groups()
                if len(groups) > 0 and groups[-1] is not None and groups[-1].isdigit():
                    if "task" in self.action_name:
                        return {"task_id": int(groups[-1])}
                    if "board" in self.action_name:
                        return {"board_id": int(groups[-1])}
        return {}

    def create_plan(self, text: str, tools: List[Type]) -> ExecutionPlan | None:
        tool_desc = f"Execute {self.action_name}"
        for t in tools:
            if t.name == self.action_name or getattr(t, 'action', None) == self.action_name:
                tool_desc = t.description
                break
                
        return ExecutionPlan(
            goal=f"Fast Execution: {self.action_name}",
            estimated_duration="~1s",
            steps=[
                PlanStep(
                    id=f"step_fast_{self.action_name}",
                    action=self.action_name,
                    arguments=self.extract_params(text),
                    description=tool_desc,
                    expected_result="Operation completes successfully."
                )
            ]
        )


class FastActionRegistry:
    def __init__(self):
        self.actions: List[FastAction] = []

    def register(self, action: FastAction):
        self.actions.append(action)

    def find_match(self, text: str) -> FastAction | None:
        text = text.strip()
        for action in self.actions:
            if action.match(text):
                return action
        return None


# Singleton instance
fast_action_registry = FastActionRegistry()

# Register core read operations
# NOTE: action names must match the `action` field on the tool class

# ListBoardsTool.action = "list_projects"
fast_action_registry.register(FastAction(
    action_name="list_projects",
    patterns=[r"^(list|show|get|fetch) (my |all )?boards$", r"^(list|show|get|fetch) (my |all )?projects$"]
))

# ListTasksTool now supports cross-board listing (no board_id required)
fast_action_registry.register(FastAction(
    action_name="list_tasks",
    patterns=[r"^(list|show|get|fetch) (my |all )?tasks$"]
))

# GetWorkspaceUsersTool.action = "get_users"
fast_action_registry.register(FastAction(
    action_name="get_users",
    patterns=[r"^(list|show|get|fetch) (all )?users$", r"^(list|show|get|fetch) (all )?members$"]
))

# GetTaskTool.action = "get_task_details"
fast_action_registry.register(FastAction(
    action_name="get_task_details",
    patterns=[r"^(get|show|fetch) task (\d+)$"]
))

fast_action_registry.register(FastAction(
    action_name="update_appearance",
    patterns=[
        r"^(switch to|use|enable|set) (dark|light|system)( mode| theme)?$",
        r"^(collapse|expand) (the )?sidebar$",
        r"^(make the sidebar|sidebar) (collapsed|expanded)$",
        r"^(restore|reset) (default|my) (appearance|theme|settings)$",
    ]
))
