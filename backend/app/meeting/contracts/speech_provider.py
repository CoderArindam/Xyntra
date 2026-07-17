"""Unified SpeechProvider interface — transcription + diarization in one call.

Providers that handle both STT and diarization atomically (Deepgram,
AssemblyAI, Azure, etc.) implement this single interface.

Business logic ONLY depends on this ABC and SpeechResult.  No provider SDK
is ever imported outside its own module.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.meeting.artifacts.recording import ProcessedAudio
from app.meeting.artifacts.speaker import SpeakerTimeline
from app.meeting.artifacts.transcript import RawTranscript


@dataclass
class SpeechResult:
    """Combined output of a unified speech processing call.

    Both artifacts are produced atomically from a single provider request.
    The pipeline stage registers them independently so downstream stages
    (normalization, alignment) remain unchanged.
    """

    transcript: RawTranscript
    timeline: SpeakerTimeline


class SpeechProvider(ABC):
    """Contract for cloud speech providers that unify STT + diarization.

    To add a new provider:
      1. Create providers/speech/<name>_provider.py implementing SpeechProvider.
      2. Register it in providers/speech/factory.py.
      3. Set MEETING_SPEECH_PROVIDER=<name> in config.
      4. Nothing else changes.
    """

    @abstractmethod
    async def process(self, audio: ProcessedAudio) -> SpeechResult:
        """Transcribe audio and produce speaker diarization in one call.

        Args:
            audio: Validated, normalized audio artifact.

        Returns:
            SpeechResult containing RawTranscript and SpeakerTimeline.

        Raises:
            SpeechProviderAuthError: Invalid API key.
            SpeechProviderRateLimitError: Rate limit hit (retryable).
            SpeechProviderTimeoutError: Request timed out (retryable).
            SpeechProviderValidationError: Bad audio or malformed response.
            SpeechProviderUnavailableError: Provider down (retryable).
            SpeechProviderError: Any other provider failure.
        """
        raise NotImplementedError
