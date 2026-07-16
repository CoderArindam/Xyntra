from typing import Dict
from app.meeting.contracts.participant_presence_provider import ParticipantPresenceProvider
from app.meeting.config import meeting_config
from app.meeting.logger import get_logger

log = get_logger("presence.registry")

class PresenceProviderRegistry:
    """Manages the lifecycle of ParticipantPresenceProvider instances.
    
    Ensures that for a given meeting session, all components (Router, Pipeline)
    share the same provider instance.
    """
    
    def __init__(self):
        self._providers: Dict[str, ParticipantPresenceProvider] = {}
        
    def get_provider(self, session_id: str) -> ParticipantPresenceProvider | None:
        """Retrieves an existing provider for the session."""
        return self._providers.get(session_id)
        
    def create_provider(self, session_id: str) -> ParticipantPresenceProvider:
        """Creates and registers a new provider for the session if it doesn't exist."""
        if session_id in self._providers:
            return self._providers[session_id]
            
        provider_name = meeting_config.PARTICIPANT_PROVIDER.lower()
        
        if provider_name == "json":
            from .json_provider import JsonPresenceProvider
            from app.meeting.config import BASE_DIR
            storage_dir = BASE_DIR / "storage" / "meeting" / "recordings"
            provider = JsonPresenceProvider(storage_dir)
        elif provider_name in ("external", "google_meet"):
            from .external_provider import ExternalPresenceProvider
            provider = ExternalPresenceProvider(meeting_id=session_id)
        else:
            raise ValueError(f"Unknown presence provider: {provider_name}")
            
        self._providers[session_id] = provider
        log.info("presence.registry.provider_created", session_id=session_id, provider_id=id(provider))
        return provider
        
    def release_provider(self, session_id: str) -> None:
        """Releases the provider associated with the session."""
        provider = self._providers.pop(session_id, None)
        if provider:
            log.info("presence.registry.provider_released", session_id=session_id, provider_id=id(provider))

# Global registry instance
presence_registry = PresenceProviderRegistry()
