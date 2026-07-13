"""TranscriptionPipeline — placeholder for speech-to-text processing.

Will be implemented in a future phase. No transcription logic yet.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("meeting.transcription")


class TranscriptionPipeline:
    """Placeholder for the transcription pipeline.

    Future responsibilities:
    - Accept audio stream / file from MeetingRecorder
    - Run speech-to-text (Whisper, Deepgram, etc.)
    - Produce timestamped transcript segments
    - Emit transcript events for downstream consumers
    """

    async def process(self, audio_path: str, session_id: str) -> dict | None:
        logger.info(
            "TranscriptionPipeline.process(%s, %s) — not yet implemented",
            audio_path, session_id,
        )
        return None

    async def stream(self, session_id: str):
        """Stream live transcription (future)."""
        logger.info("TranscriptionPipeline.stream(%s) — not yet implemented", session_id)
        return None
