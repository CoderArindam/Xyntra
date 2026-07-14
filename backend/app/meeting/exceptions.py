"""Meeting module — rich, typed exceptions.

Every error exposes: code, message, recoverable, retryable.
This makes upstream handling, logging, and future AI explanations deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MeetingError(Exception):
    """Base class for all meeting module errors."""

    code: str
    message: str
    recoverable: bool = False
    retryable: bool = False

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"

    def __post_init__(self) -> None:
        super().__init__(self.message)


class BrowserLaunchError(MeetingError):
    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(
            code="BROWSER_LAUNCH_ERROR",
            message=message,
            recoverable=False,
            retryable=retryable,
        )


class AuthenticationError(MeetingError):
    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(
            code="AUTH_ERROR",
            message=message,
            recoverable=False,
            retryable=retryable,
        )


class MeetingJoinError(MeetingError):
    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(
            code="JOIN_ERROR",
            message=message,
            recoverable=False,
            retryable=retryable,
        )


class LobbyTimeoutError(MeetingError):
    def __init__(self, message: str = "Timed out waiting for lobby admission") -> None:
        super().__init__(
            code="LOBBY_TIMEOUT",
            message=message,
            recoverable=False,
            retryable=False,
        )


class PermissionDeniedError(MeetingError):
    def __init__(self, message: str = "Permission denied to join this meeting") -> None:
        super().__init__(
            code="PERMISSION_DENIED",
            message=message,
            recoverable=False,
            retryable=False,
        )


class NetworkError(MeetingError):
    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(
            code="NETWORK_ERROR",
            message=message,
            recoverable=True,
            retryable=retryable,
        )


class ProfileLockError(MeetingError):
    def __init__(self, message: str) -> None:
        super().__init__(
            code="PROFILE_LOCK_ERROR",
            message=message,
            recoverable=False,
            retryable=True,
        )


class ProviderNotFoundError(MeetingError):
    def __init__(self, meeting_url: str) -> None:
        super().__init__(
            code="PROVIDER_NOT_FOUND",
            message=f"No meeting provider found for URL: {meeting_url}",
            recoverable=False,
            retryable=False,
        )


class RecordingInitError(MeetingError):
    """Audio capture could not be initialized (e.g., no audio stream available)."""
    def __init__(self, message: str) -> None:
        super().__init__(
            code="RECORDING_INIT_ERROR",
            message=message,
            recoverable=False,
            retryable=False,
        )


class RecordingWriteError(MeetingError):
    """Failed to write recording data to storage."""
    def __init__(self, message: str) -> None:
        super().__init__(
            code="RECORDING_WRITE_ERROR",
            message=message,
            recoverable=False,
            retryable=False,
        )


class RecordingValidationError(MeetingError):
    """Recording failed validation (corrupt, too short, missing audio, etc.)."""
    def __init__(self, message: str) -> None:
        super().__init__(
            code="RECORDING_VALIDATION_ERROR",
            message=message,
            recoverable=False,
            retryable=False,
        )


class AudioProcessingError(MeetingError):
    """Audio processing/normalization failed (FFmpeg error, IO error, etc.)."""
    def __init__(self, message: str) -> None:
        super().__init__(
            code="AUDIO_PROCESSING_ERROR",
            message=message,
            recoverable=False,
            retryable=True,
        )


class SpeechToTextError(MeetingError):
    """Speech-to-Text provider failed (e.g., model load error, out of memory)."""
    def __init__(self, message: str) -> None:
        super().__init__(
            code="SPEECH_TO_TEXT_ERROR",
            message=message,
            recoverable=False,
            retryable=True,
        )
