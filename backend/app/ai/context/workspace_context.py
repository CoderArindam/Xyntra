from typing import Any, Dict
from app.ai.context.base import BaseContextBuilder
import asyncpg

class WorkspaceContextBuilder(BaseContextBuilder):
    """
    Builds context related to the user's workspace.
    In Phase 3.2, this ONLY provides identity and navigation context.
    The AI must fetch actual board/task data via Tool Execution.
    """
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def build(self, current_user: dict, board_id: int = None, **kwargs: Any) -> Dict[str, Any]:
        # Provide only lightweight identity and navigation context
        user_identity = f"{current_user.get('first_name')} {current_user.get('last_name')} ({current_user.get('email')})"
        
        context = {
            "current_user": user_identity,
            "current_board_id": board_id if board_id else "None"
        }
        
        return context
