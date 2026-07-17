"""Speech provider factory.

Reads MEETING_SPEECH_PROVIDER from config and returns the active SpeechProvider.
Adding a new provider requires only adding a branch here and creating its module.
"""

from __future__ import annotations

from app.meeting.config import meeting_config
from app.meeting.contracts.speech_provider import SpeechProvider
from app.meeting.exceptions import SpeechProviderConfigError


def get_speech_provider() -> SpeechProvider:
    """Return the active SpeechProvider instance.

    Raises:
        SpeechProviderConfigError: If MEETING_SPEECH_PROVIDER is unknown.
    """
    provider_name = meeting_config.SPEECH_PROVIDER.lower()

    if provider_name == "deepgram":
        from app.meeting.providers.speech.deepgram_provider import DeepgramSpeechProvider
        return DeepgramSpeechProvider()

    # Future providers plug in here:
    # if provider_name == "google":
    #     from app.meeting.providers.speech.google_provider import GoogleSpeechProvider
    #     return GoogleSpeechProvider()
    # if provider_name == "assemblyai":
    #     from app.meeting.providers.speech.assemblyai_provider import AssemblyAISpeechProvider
    #     return AssemblyAISpeechProvider()
    # if provider_name == "azure":
    #     from app.meeting.providers.speech.azure_provider import AzureSpeechProvider
    #     return AzureSpeechProvider()

    raise SpeechProviderConfigError(
        f"Unknown speech provider: '{provider_name}'. "
        f"Set MEETING_SPEECH_PROVIDER to one of: deepgram"
    )
