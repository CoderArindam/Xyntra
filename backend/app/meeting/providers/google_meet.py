"""GoogleMeetProvider — wires together GoogleAuthService and GoogleMeetJoiner.

This is the only Google-specific file in the provider layer.
MeetingService never imports from bot.browser or bot.joiner directly.
"""

from __future__ import annotations

from typing import Any

from app.meeting.bot.browser.google_auth import GoogleAuthService
from app.meeting.bot.joiner.bot import GoogleMeetJoiner
from app.meeting.models.session import JoinState
from app.meeting.providers.base import MeetingProvider
from app.meeting.utils.google_selectors import GOOGLE_MEET_URL_PATTERN


class GoogleMeetProvider(MeetingProvider):
    """Handles joining and leaving Google Meet sessions."""

    def __init__(self, auth_service: GoogleAuthService, joiner: GoogleMeetJoiner) -> None:
        self._auth = auth_service
        self._joiner = joiner

    # ------------------------------------------------------------------ #
    # MeetingProvider contract                                             #
    # ------------------------------------------------------------------ #

    def can_handle(self, meeting_url: str) -> bool:
        return GOOGLE_MEET_URL_PATTERN in meeting_url

    async def ensure_authenticated(self, page: Any) -> None:
        await self._auth.ensure_authenticated(page)

    async def join(self, page: Any, meeting_url: str, bot_name: str) -> JoinState:
        await self._auth.ensure_authenticated(page)
        return await self._joiner.join(page, meeting_url, bot_name)

    async def leave(self, page: Any) -> None:
        await self._joiner.leave(page)
