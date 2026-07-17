"""Speech providers package."""

from .deepgram_provider import DeepgramSpeechProvider
from .factory import get_speech_provider

__all__ = ["DeepgramSpeechProvider", "get_speech_provider"]
