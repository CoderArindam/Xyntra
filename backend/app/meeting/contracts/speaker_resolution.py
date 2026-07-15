from abc import ABC, abstractmethod
from typing import Optional

from app.meeting.artifacts.speaker import (
    SpeakerAttributedTranscript,
    SpeakerMapping,
    ParticipantAttributedTranscript,
)


class SpeakerResolutionProvider(ABC):
    """Contract for resolving anonymous speaker labels to participant identities.

    Consumes a SpeakerAttributedTranscript (Speaker_01 labels) and a
    SpeakerMapping (Speaker_01 → participant) and produces the final
    ParticipantAttributedTranscript.

    The SpeakerMapping is always produced by SpeakerMappingService before
    this provider is called.  This provider never performs mapping itself —
    it only applies an existing mapping to a transcript.
    """

    @abstractmethod
    async def resolve(
        self,
        attributed: SpeakerAttributedTranscript,
        mapping: Optional[SpeakerMapping],
    ) -> ParticipantAttributedTranscript:
        """Apply a speaker mapping to produce participant-attributed segments.

        When mapping is None, all segments are returned with participant_id=None.
        speaker_label is always preserved regardless of resolution outcome.
        """
        raise NotImplementedError
