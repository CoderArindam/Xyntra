from abc import ABC, abstractmethod

from app.meeting.artifacts.speaker import ParticipantRoster


class ParticipantRosterProvider(ABC):
    """Contract for fetching meeting participant rosters.
    
    This abstracts away whether the roster comes from a local JSON file (development)
    or the Google Meet integration (production).
    """

    @abstractmethod
    async def get_roster(self, meeting_id: str, **kwargs) -> ParticipantRoster:
        """Fetch the participant roster for a given meeting session."""
        pass
