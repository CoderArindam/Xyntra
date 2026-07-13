"""Abstract meeting provider interface.

Every supported meeting platform (Google Meet, Zoom, Teams, etc.)
implements this ABC. MeetingService only depends on this interface —
never on any platform-specific implementation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.meeting.models.session import JoinState


class MeetingProvider(ABC):
    """Contract that all meeting platform providers must fulfil."""

    @abstractmethod
    def can_handle(self, meeting_url: str) -> bool:
        """Return True if this provider supports the given meeting URL."""

    @abstractmethod
    async def ensure_authenticated(self, page: Any) -> None:
        """Ensure the browser page is authenticated for this platform.

        Should be idempotent — safe to call even when already authenticated.

        Raises:
            AuthenticationError: If authentication cannot be established.
        """

    @abstractmethod
    async def join(self, page: Any, meeting_url: str, bot_name: str) -> JoinState:
        """Navigate to and join the meeting.

        Args:
            page: An authenticated Playwright Page.
            meeting_url: The full meeting URL.
            bot_name: Display name for the bot in the meeting.

        Returns:
            JoinState describing the result (IN_MEETING, WAITING_FOR_ADMISSION, etc.).
        """

    @abstractmethod
    async def leave(self, page: Any) -> None:
        """Leave the current meeting.

        Should not raise — use best-effort (click leave or close page).
        """
