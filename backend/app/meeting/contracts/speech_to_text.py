from abc import ABC, abstractmethod
from app.meeting.artifacts import ProcessedAudio, RawTranscript


class SpeechToTextProvider(ABC):
    """Contract for speech-to-text transcription."""

    @abstractmethod
    async def transcribe(self, audio: ProcessedAudio) -> RawTranscript:
        """Convert processed audio into a raw transcript."""
        raise NotImplementedError
