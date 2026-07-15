from abc import ABC, abstractmethod
from typing import Optional

from app.meeting.artifacts.speaker import SpeakerTimeline, SpeakerAttributedTranscript
from app.meeting.artifacts.transcript import NormalizedTranscript


class SpeakerAlignmentProvider(ABC):
    """Contract for aligning transcript segments to speaker turns.

    Matches NormalizedTranscript segments against SpeakerTimeline turns
    by timestamp overlap and produces a SpeakerAttributedTranscript.

    Operates on anonymous speaker labels only (Speaker_01…).
    Participant identity resolution is a separate concern handled by
    SpeakerResolutionProvider.
    """

    @abstractmethod
    async def align(
        self,
        transcript: NormalizedTranscript,
        timeline: Optional[SpeakerTimeline],
    ) -> SpeakerAttributedTranscript:
        """Annotate transcript segments with speaker labels from the timeline.

        When timeline is None, all segments are returned with speaker_label=None.
        """
        raise NotImplementedError
