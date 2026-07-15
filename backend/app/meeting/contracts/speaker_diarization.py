from abc import ABC, abstractmethod

from app.meeting.artifacts.recording import ProcessedAudio
from app.meeting.artifacts.speaker import SpeakerTimeline


class SpeakerDiarizationProvider(ABC):
    """Contract for speaker diarization.

    Every diarization provider (Pyannote, AssemblyAI, NeMo, Azure, etc.)
    implements this interface and returns a SpeakerTimeline artifact.

    The rest of the pipeline — alignment, mapping, resolution — depends
    only on this interface.  No concrete provider is ever imported outside
    its own module.
    """

    @abstractmethod
    async def diarize(self, audio: ProcessedAudio) -> SpeakerTimeline:
        """Identify speaker turns in processed audio and return a SpeakerTimeline."""
        raise NotImplementedError
