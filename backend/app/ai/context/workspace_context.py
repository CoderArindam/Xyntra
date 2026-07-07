from typing import Any, Dict
from app.ai.context.base import BaseContextBuilder
import asyncpg


class WorkspaceContextBuilder(BaseContextBuilder):
    """
    Builds identity and navigation context for the AI planner.
    Provides structured user fields and board names so the planner can
    resolve 'me', 'my tasks', board names, etc. without extra LLM calls.
    """
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def build(self, current_user: dict, board_id: int = None, **kwargs: Any) -> Dict[str, Any]:
        first_name = current_user.get('first_name', '')
        last_name = current_user.get('last_name', '')
        email = current_user.get('email', '')
        user_id = current_user.get('id')
        org_id = current_user.get('organization_id')
        
        # Fetch user's board names for entity resolution
        board_names = []
        try:
            rows = await self.conn.fetch(
                "SELECT id, name FROM v_boards_canonical WHERE organization_id = $1 AND can_view_board($2, id) AND archived_at IS NULL",
                org_id, user_id
            )
            board_names = [{"id": r["id"], "name": r["name"]} for r in rows]
        except Exception:
            pass
        
        context = {
            "current_user": f"{first_name} {last_name} ({email})",
            "current_user_first_name": first_name,
            "current_user_last_name": last_name,
            "current_user_email": email,
            "current_user_id": user_id,
            "current_board_id": board_id if board_id else "None",
            "available_boards": board_names,
        }
        
        return context
