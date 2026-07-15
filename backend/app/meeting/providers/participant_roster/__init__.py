"""Participant Roster Provider registry and factory."""

from app.meeting.config import meeting_config
from app.meeting.contracts.participant_roster_provider import ParticipantRosterProvider
from app.meeting.exceptions import MeetingError
from .json_provider import JsonParticipantRosterProvider
from .google_provider import GoogleMeetParticipantProvider

_PROVIDERS = {
    "json": JsonParticipantRosterProvider,
    "google": GoogleMeetParticipantProvider,
}

def get_roster_provider() -> ParticipantRosterProvider:
    provider_name = meeting_config.PARTICIPANT_PROVIDER
    provider_cls = _PROVIDERS.get(provider_name)
    if not provider_cls:
        raise MeetingError(
            code="UNKNOWN_ROSTER_PROVIDER",
            message=f"Unknown PARTICIPANT_PROVIDER: {provider_name}",
        )
    return provider_cls()
