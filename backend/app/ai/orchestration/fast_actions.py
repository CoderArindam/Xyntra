import re
from typing import Dict, Any, Callable, List, Type
from pydantic import BaseModel
from app.ai.schemas.planning import ExecutionPlan, PlanStep

class FastAction(BaseModel):
    action_name: str
    patterns: List[str]
    # In a real app, you'd use re.compile, we'll compile them on load
    _compiled_patterns: List[re.Pattern] = []

    def __init__(self, **data):
        super().__init__(**data)
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.patterns]

    def match(self, text: str) -> bool:
        return any(p.match(text) for p in self._compiled_patterns)
        
    def extract_params(self, text: str) -> Dict[str, Any]:
        """Extract parameters from regex capture groups."""
        for p in self._compiled_patterns:
            match = p.match(text)
            if match:
                groups = match.groups()
                # Simple heuristic: if we have a group that's just digits, assume it's an ID
                # In a real app we'd map groups to schema fields.
                # For `get_task (\d+)`, we map it to task_id
                if len(groups) > 0 and groups[-1].isdigit():
                    if "task" in self.action_name:
                        return {"task_id": int(groups[-1])}
                    if "board" in self.action_name:
                        return {"board_id": int(groups[-1])}
        return {}

    def create_plan(self, text: str, tools: List[Type]) -> ExecutionPlan | None:
        """Constructs an ExecutionPlan if valid."""
        # Find the tool description
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

# Register core read operations safely
fast_action_registry.register(FastAction(
    action_name="list_boards",
    patterns=[r"^(list|show|get|fetch) (my )?boards$"]
))

fast_action_registry.register(FastAction(
    action_name="list_tasks",
    patterns=[r"^(list|show|get|fetch) (my )?tasks$"]
))

fast_action_registry.register(FastAction(
    action_name="get_workspace_users",
    patterns=[r"^(list|show|get|fetch) (all )?users$"]
))

fast_action_registry.register(FastAction(
    action_name="get_task",
    patterns=[r"^(get|show|fetch) task (\d+)$"]
))
