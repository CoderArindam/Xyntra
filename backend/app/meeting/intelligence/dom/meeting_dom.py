"""MeetingDOM — the only file that knows Google Meet state banner selectors.

Scans DOM in priority order to determine the current MeetingState.
First match wins. When Meet changes its error/info banners, only this file
needs updating.
"""

from __future__ import annotations

from typing import Any

from app.meeting.intelligence.models import MeetingState
from app.meeting.logger import get_logger
from app.meeting.utils.google_selectors import MEET_SELECTORS as SEL

log = get_logger("intelligence.dom.meeting")

# Priority-ordered detection: terminal states checked before transient states
_STATE_SELECTOR_MAP: list[tuple[str, MeetingState]] = [
    ("empty_meeting_popup", MeetingState.EMPTY_POPUP),
    ("bot_removed_dialog",  MeetingState.BOT_REMOVED),
    ("host_ended_meeting",  MeetingState.HOST_ENDED),
    ("meeting_ended",       MeetingState.ENDED),
    ("permission_denied",   MeetingState.DENIED_ENTRY),
    ("reconnecting_dialog", MeetingState.RECONNECTING),
    ("network_lost_banner", MeetingState.NETWORK_LOST),
    ("waiting_for_host",    MeetingState.WAITING_FOR_HOST),
    ("waiting_room_text",   MeetingState.LOBBY),
    ("meeting_controls",    MeetingState.IN_MEETING),
]


class MeetingDOM:
    """Queries DOM to determine current meeting state.

    Returns MeetingState.UNKNOWN when no selector matches.
    """

    async def detect_state(self, page: Any) -> MeetingState:
        """Scan selectors in priority order. Returns first matched state."""
        for selector_key, state in _STATE_SELECTOR_MAP:
            try:
                el = page.locator(SEL[selector_key])
                if await el.count() > 0:
                    return state
            except Exception:
                continue
        return MeetingState.UNKNOWN
