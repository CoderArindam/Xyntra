"""Abstract base class for all Speaker Mapping Strategies.

A mapping strategy correlates an anonymous SpeakerTimeline (who spoke when)
with a ParticipantRoster (who joined the meeting) to produce a SpeakerMapping.
"""
from abc import ABC, abstractmethod
from typing import Optional

from app.meeting.artifacts.speaker import (
    ParticipantRoster,
    SpeakerMapping,
    SpeakerTimeline,
)


class SpeakerMappingStrategy(ABC):
    """Abstract interface for all speaker mapping strategies."""

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """The unique identifier for this strategy (e.g. 'dummy', 'join_order')."""
        pass

    @abstractmethod
    async def build_mapping(
        self,
        timeline: SpeakerTimeline,
        roster: Optional[ParticipantRoster],
    ) -> SpeakerMapping:
        """Produce a deterministic mapping from speaker labels to participants."""
        pass
