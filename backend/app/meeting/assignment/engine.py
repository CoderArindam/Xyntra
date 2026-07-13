"""AssignmentEngine — placeholder for assigning extracted tasks to users.

Will be implemented in a future phase. No assignment logic yet.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("meeting.assignment")


class AssignmentEngine:
    """Placeholder for the task assignment engine.

    Future responsibilities:
    - Accept extracted task candidates
    - Match tasks to workspace members
    - Create tasks on the Kanban board via KAIO APIs
    """

    async def assign(self, tasks: list[dict], session_id: str) -> list[dict]:
        logger.info(
            "AssignmentEngine.assign(%d tasks, %s) — not yet implemented",
            len(tasks), session_id,
        )
        return []
