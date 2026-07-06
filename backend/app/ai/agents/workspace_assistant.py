from typing import Any, Dict, List
from app.ai.agents.base import BaseAgent
from app.ai.prompts.registry import PromptRegistry
from app.ai.tools.workspace_tools import GetTaskTool, ListBoardsTool, ListTasksTool, GetWorkspaceUsersTool

class WorkspaceAssistantAgent(BaseAgent):
    """
    Main assistant agent for handling user workspace queries.
    """
    name = "workspace_assistant"
    available_tools = [ListBoardsTool, ListTasksTool, GetWorkspaceUsersTool, GetTaskTool]

    def build_messages(self, user_input: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        workspace_context_str = f"""
Current User: {context.get('current_user', 'Unknown')}
Current Board ID UI Context: {context.get('current_board_id', 'None')}
        """.strip()

        system_prompt = PromptRegistry.render_prompt(
            agent_name=self.name,
            prompt_name="system",
            context={"workspace_context": workspace_context_str},
            version="v1"
        )
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
