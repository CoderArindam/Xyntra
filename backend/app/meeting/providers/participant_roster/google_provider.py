"""Google Meet participant roster provider for production mode."""

from app.meeting.artifacts.speaker import ParticipantRoster
from app.meeting.contracts.participant_roster_provider import ParticipantRosterProvider
from app.meeting.exceptions import ParticipantProviderUnavailable


class GoogleMeetParticipantProvider(ParticipantRosterProvider):
    """Fetches meeting participants from the Google Meet integration.
    
    This is a placeholder for the future M2.8+ integration.
    """

    async def get_roster(self, meeting_id: str, **kwargs) -> ParticipantRoster:
        raise ParticipantProviderUnavailable(
            "Google Meet participant provider has not been implemented yet."
        )
