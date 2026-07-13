"""Provider factory — resolves the correct MeetingProvider for a URL.

Usage:
    provider = get_provider(meeting_url)
    join_state = await provider.join(page, meeting_url, bot_name)

To add a new platform (Zoom, Teams, etc.):
1. Create providers/zoom.py implementing MeetingProvider.
2. Register it in _PROVIDER_FACTORIES below.
"""

from __future__ import annotations

from app.meeting.config import meeting_config
from app.meeting.bot.browser.google_auth import GoogleAuthService
from app.meeting.bot.joiner.bot import GoogleMeetJoiner
from app.meeting.exceptions import ProviderNotFoundError
from app.meeting.providers.base import MeetingProvider
from app.meeting.providers.google_meet import GoogleMeetProvider
from app.meeting.utils.google_selectors import GOOGLE_MEET_URL_PATTERN


def _create_google_meet_provider() -> GoogleMeetProvider:
    auth = GoogleAuthService(
        email=meeting_config.GOOGLE_EMAIL,
        password=meeting_config.GOOGLE_PASSWORD,
    )
    joiner = GoogleMeetJoiner()
    return GoogleMeetProvider(auth, joiner)


# Registry: URL substring → factory function
_PROVIDER_FACTORIES: list[tuple[str, callable]] = [
    (GOOGLE_MEET_URL_PATTERN, _create_google_meet_provider),
]


def get_provider(meeting_url: str) -> MeetingProvider:
    """Return the appropriate MeetingProvider for the given URL.

    Raises:
        ProviderNotFoundError: If no registered provider handles the URL.
    """
    for url_pattern, factory in _PROVIDER_FACTORIES:
        if url_pattern in meeting_url:
            return factory()
    raise ProviderNotFoundError(meeting_url)


__all__ = ["get_provider", "MeetingProvider"]
