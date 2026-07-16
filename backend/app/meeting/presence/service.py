"""Participant presence coordination service."""

from app.meeting.artifacts.speaker import ParticipantPresenceTimeline
from app.meeting.contracts.participant_presence_provider import ParticipantPresenceProvider


class ParticipantPresenceService:
    """Coordinates fetching presence timelines from the underlying provider."""
    
    def __init__(self, provider: ParticipantPresenceProvider):
        self.provider = provider
        
    async def collect(self, meeting_id: str) -> ParticipantPresenceTimeline:
        """Collects the full presence timeline for a given meeting."""
        return await self.provider.collect(meeting_id)
