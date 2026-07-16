from abc import ABC, abstractmethod
from typing import Any

from app.meeting.artifacts.speaker import ParticipantPresenceTimeline

class ParticipantPresenceProvider(ABC):
    """
    Base contract for providing participant presence events.
    """

    @abstractmethod
    async def start(self) -> None:
        pass

    @abstractmethod
    async def stop(self) -> None:
        pass

    @abstractmethod
    async def collect(self, meeting_id: str, **kwargs: Any) -> ParticipantPresenceTimeline:
        pass
