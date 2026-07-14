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

    async def get_raw_participants(self, page: Any) -> list[dict[str, Any]]:
        """Scrape the participant list from video tiles.

        Returns:
            List of {"name": str, "is_host": bool, "avatar_url": str | None, "is_self": bool}.
            Empty list if scraping fails or no participants are found.
        """
        log.debug("participant_dom.scan_started")
        results: list[dict[str, Any]] = []
        try:
            items = page.locator(SEL["participant_list_item"])
            count = await items.count()
            log.debug("participant_dom.tiles_found", count=count)
            names_found = 0

            for i in range(count):
                item = items.nth(i)
                try:
                    # Get all text inside the tile to check for self indicators (including hidden tooltips)
                    row_text = await item.text_content() or ""
                    
                    # Extract the exact name using the deterministic span selector
                    name_els = item.locator(SEL["participant_name_in_item"])
                    name_texts = await name_els.all_inner_texts()
                    
                    # Find the first non-empty name text
                    raw_name = ""
                    for nt in name_texts:
                        if nt.strip():
                            raw_name = nt.strip()
                            break
                            
                    if not raw_name:
                        log.debug("participant_dom.name_extraction_failed", tile_index=i)
                        continue

                    names_found += 1

                    # Detect and strip host badge
                    is_host = bool(_HOST_BADGE.search(raw_name))
                    clean_name = _HOST_BADGE.sub("", raw_name).strip()

                    # Strip self-reference suffixes or detect self via text context
                    is_self = (
                        bool(_SELF_SUFFIXES.search(row_text)) 
                        or "(you)" in row_text.lower()
                        or "Others might still see your full video." in row_text
                    )
                    clean_name = _SELF_SUFFIXES.sub("", clean_name).strip()

                    avatar_url: str | None = None
                    try:
                        img = item.locator("img")
                        if await img.count() > 0:
                            avatar_url = await img.first.get_attribute("src")
                    except Exception:
                        pass

                    results.append({"name": clean_name, "is_host": is_host, "is_self": is_self, "avatar_url": avatar_url})
                except Exception as exc:
                    log.debug("participant_dom.selector_failed", tile_index=i, error=str(exc))
                    continue

            log.debug("participant_dom.names_found", count=names_found)
        except Exception as exc:
            log.warning("Participant list DOM query failed", error=str(exc))
            
        log.debug("participant_dom.participants_returned", count=len(results))
        log.debug("participant_dom.scan_completed")
        return results

    async def get_self_display_name(self, page: Any) -> str | None:
        """Return what Google Meet shows as the bot's own name by finding the self tile."""
        participants = await self.get_raw_participants(page)
        for p in participants:
            if p.get("is_self"):
                return p["name"]
        return None

