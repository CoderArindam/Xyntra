"""TaskExtractionPipeline — placeholder for extracting tasks from transcripts.

Will be implemented in a future phase. No extraction logic yet.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("meeting.extraction")


class TaskExtractionPipeline:
    """Placeholder for the task extraction pipeline.

    Future responsibilities:
    - Accept a transcript
    - Use LLM to identify action items, decisions, follow-ups
    - Produce structured task candidates
    """

    async def extract(self, transcript: dict, session_id: str) -> list[dict]:
        logger.info(
            "TaskExtractionPipeline.extract(%s) — not yet implemented", session_id,
        )
        return []
