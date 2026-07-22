from app.meeting.contracts.participant_presence_provider import ParticipantPresenceProvider
from app.meeting.config import meeting_config
from .json_provider import JsonPresenceProvider
from .external_provider import ExternalPresenceProvider
from .registry import presence_registry, PresenceProviderRegistry

def get_presence_provider(*args, **kwargs) -> ParticipantPresenceProvider:
    meeting_id = kwargs.get("meeting_id", "default_meeting")
    return presence_registry.create_provider(meeting_id)
