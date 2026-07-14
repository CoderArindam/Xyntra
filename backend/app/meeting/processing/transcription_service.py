"""Speech-to-Text Transcription Service.

Orchestrates the conversion of ProcessedAudio into a RawTranscript using
an injected SpeechToTextProvider.
"""

from __future__ import annotations

from app.meeting.artifacts.recording import ProcessedAudio
from app.meeting.artifacts.transcript import RawTranscript
from app.meeting.contracts.speech_to_text import SpeechToTextProvider
from app.meeting.exceptions import SpeechToTextError
from app.meeting.logger import get_logger

log = get_logger("meeting.stt.service")


class TranscriptionService:
    """Service to generate raw transcripts from processed audio."""

    def __init__(self, provider: SpeechToTextProvider) -> None:
        self._provider = provider

    async def process(self, audio: ProcessedAudio) -> RawTranscript:
        """Generate an immutable RawTranscript from ProcessedAudio."""
        log.info(
            "transcription.service.started",
            processed_audio_id=audio.id,
            meeting_id=audio.meeting_id,
        )

        try:
            transcript = await self._provider.transcribe(audio)
            
            # The provider should return a valid RawTranscript artifact
            # For this phase, we are simply passing it through. No normalization.
            
            log.info(
                "transcription.service.completed",
                processed_audio_id=audio.id,
                artifact_id=transcript.id,
                segment_count=len(transcript.segments),
            )
            return transcript
            
        except SpeechToTextError:
            raise
        except Exception as exc:
            log.error("transcription.service.failed", processed_audio_id=audio.id, error=str(exc))
            raise SpeechToTextError(f"Unexpected STT failure: {exc}") from exc
