"""SpeakerDOM — the only file that knows Google Meet speaker detection selectors.

Tries multiple strategies in priority order; returns None if no speaker is
detectable (silence, muted, or panel not visible).
"""

from __future__ import annotations

from typing import Any

from app.meeting.logger import get_logger
from app.meeting.utils.google_selectors import MEET_SELECTORS as SEL

log = get_logger("intelligence.dom.speaker")

_TIMEOUT_MS = 500


class SpeakerDOM:
    """Queries the active speaker indicator in the Meet UI.

    No audio capture. Observation only.
    """

    async def get_active_speaker_name(self, page: Any) -> str | None:
        """Return the display name of the currently active speaker.

        Tries three strategies in order:
        1. Element explicitly marked with speaking-indicator attribute
        2. Active speaker label text element
        3. Video tile with speaking animation class
        Returns None on silence or failure.
        """
        # Strategy 1: direct speaking indicator label
        for key in ("speaking_indicator_name", "active_speaker_label"):
            try:
                el = page.locator(SEL[key])
                if await el.count() > 0:
                    name = (await el.first.inner_text(timeout=_TIMEOUT_MS)).strip()
                    if name:
                        log.debug("Speaker detected via strategy 1", key=key, name=name)
                        return name
            except Exception:
                continue

        # Strategy 2: video tile with speaking ring
        try:
            tiles = page.locator(SEL["speaking_video_tile"])
            if await tiles.count() > 0:
                name_el = tiles.first.locator(SEL["video_tile_name"])
                if await name_el.count() > 0:
                    name = (await name_el.first.inner_text(timeout=_TIMEOUT_MS)).strip()
                    if name:
                        log.debug("Speaker detected via strategy 2 (tile)", name=name)
                        return name
        except Exception:
            pass

        return None
