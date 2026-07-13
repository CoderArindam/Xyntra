"""ParticipantDOM — the only file that knows Google Meet participant selectors.

All Playwright calls for participant-related DOM live here.
When Meet changes its participant panel UI, only this file needs updating.
"""

from __future__ import annotations

import re
from typing import Any

from app.meeting.logger import get_logger
from app.meeting.utils.google_selectors import MEET_SELECTORS as SEL

log = get_logger("intelligence.dom.participant")

_PANEL_OPEN_TIMEOUT_MS = 3_000
_INNER_TEXT_TIMEOUT_MS = 500

# Suffixes Google Meet appends to the bot's own tile (localized variants)
_SELF_SUFFIXES = re.compile(r"\s*\((you|presentation)\)\s*$", re.IGNORECASE)

# Host badge Meet may append to the host's tile name
_HOST_BADGE = re.compile(r"\s*\(host\)\s*$", re.IGNORECASE)


class ParticipantDOM:
    """Handles all DOM queries for participant panel data.

    Returns normalized Python dicts — no Playwright objects escape this class.
    """

    async def ensure_panel_open(self, page: Any) -> bool:
        """Open the People side panel if it isn't already visible.

        Returns True when the panel is confirmed open, False on failure.
        Note: opening the panel changes visible UI but has no meeting impact.
        """
        try:
            container = page.locator(SEL["participant_panel_container"])
            if await container.count() > 0:
                return True

            btn = page.locator(SEL["participants_panel_btn"])
            if await btn.count() > 0:
                await btn.first.click()
                await page.wait_for_selector(
                    SEL["participant_panel_container"],
                    timeout=_PANEL_OPEN_TIMEOUT_MS,
                )
                return True
        except Exception as exc:
            log.warning("Could not open participant panel", error=str(exc))
        return False

    async def get_raw_participants(self, page: Any) -> list[dict[str, Any]]:
        """Scrape the participant list.

        Returns:
            List of {"name": str, "is_host": bool, "avatar_url": str | None}.
            Empty list if the panel is absent or scraping fails.
        """
        results: list[dict[str, Any]] = []
        try:
            items = page.locator(SEL["participant_list_item"])
            count = await items.count()
            for i in range(count):
                item = items.nth(i)
                try:
                    raw_name = await item.locator(SEL["participant_name_in_item"]).inner_text(
                        timeout=_INNER_TEXT_TIMEOUT_MS
                    )
                    raw_name = raw_name.strip()
                    if not raw_name:
                        continue

                    # Detect and strip host badge
                    is_host = bool(_HOST_BADGE.search(raw_name))
                    clean_name = _HOST_BADGE.sub("", raw_name).strip()

                    # Strip self-reference suffixes (bot's own tile)
                    clean_name = _SELF_SUFFIXES.sub("", clean_name).strip()

                    avatar_url: str | None = None
                    try:
                        img = item.locator("img[src]")
                        if await img.count() > 0:
                            avatar_url = await img.first.get_attribute("src", timeout=_INNER_TEXT_TIMEOUT_MS)
                    except Exception:
                        pass

                    results.append({"name": clean_name, "is_host": is_host, "avatar_url": avatar_url})
                except Exception:
                    continue

        except Exception as exc:
            log.warning("Participant list DOM query failed", error=str(exc))
        return results

    async def get_self_display_name(self, page: Any) -> str | None:
        """Return what Google Meet shows as the bot's own name."""
        for selector_key in ("self_participant_name", "self_name_fallback"):
            try:
                el = page.locator(SEL[selector_key])
                if await el.count() > 0:
                    name = (await el.first.inner_text(timeout=_INNER_TEXT_TIMEOUT_MS)).strip()
                    name = _SELF_SUFFIXES.sub("", name).strip()
                    if name:
                        return name
            except Exception:
                continue
        return None
