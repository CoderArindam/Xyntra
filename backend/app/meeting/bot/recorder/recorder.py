"""MeetingRecorder — placeholder for audio/video capture.

Will be implemented in a future phase. No recording logic yet.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("meeting.bot.recorder")


class MeetingRecorder:
    """Placeholder for meeting recording capabilities.

    Future responsibilities:
    - Capture browser tab audio
    - Record meeting audio stream
    - Save recordings to configured path
    - Provide recording status
    """

    def __init__(self) -> None:
        self._recording = False
        logger.debug("MeetingRecorder initialized (stub)")

    @property
    def is_recording(self) -> bool:
        return self._recording

    async def start(self, session_id: str) -> None:
        logger.info("MeetingRecorder.start(%s) — not yet implemented", session_id)

    async def stop(self) -> str | None:
        """Stop recording and return the file path (None in stub)."""
        logger.info("MeetingRecorder.stop() — not yet implemented")
        self._recording = False
        return None

    async def cleanup(self) -> None:
        logger.info("MeetingRecorder.cleanup()")
        self._recording = False
