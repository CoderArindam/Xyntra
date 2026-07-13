"""Debug capture — saves diagnostic artifacts on any meeting failure.

Artifacts saved per failure event:
  - screenshot.png
  - page.html
  - console.log
  - info.json  (url, title, timestamp)

Stored under: {DEBUG_DIR}/{session_id}/{label}_{timestamp}/
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.meeting.logger import get_logger

log = get_logger("utils.debug")


class DebugCapture:
    """Captures full-page diagnostic artifacts from a Playwright page."""

    def __init__(self, debug_dir: str) -> None:
        self._base = Path(debug_dir)

    async def capture(
        self,
        page: Any,
        session_id: str,
        label: str = "failure",
    ) -> str:
        """Save all available debug artifacts and return the artifact directory path."""
        ts = int(time.time())
        artifact_dir = self._base / session_id / f"{label}_{ts}"
        artifact_dir.mkdir(parents=True, exist_ok=True)

        await self._save_screenshot(page, artifact_dir)
        await self._save_html(page, artifact_dir)
        await self._save_info(page, artifact_dir)
        await self._save_console(page, artifact_dir)

        log.info(
            "Debug artifacts saved",
            session_id=session_id,
            label=label,
            path=str(artifact_dir),
        )
        return str(artifact_dir)

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    async def _save_screenshot(self, page: Any, dest: Path) -> None:
        try:
            await page.screenshot(path=str(dest / "screenshot.png"), full_page=True)
        except Exception as exc:
            log.warning("Screenshot capture failed", error=str(exc))

    async def _save_html(self, page: Any, dest: Path) -> None:
        try:
            html = await page.content()
            (dest / "page.html").write_text(html, encoding="utf-8", errors="replace")
        except Exception as exc:
            log.warning("HTML capture failed", error=str(exc))

    async def _save_info(self, page: Any, dest: Path) -> None:
        try:
            info = {
                "url": page.url,
                "title": await page.title(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            (dest / "info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
        except Exception as exc:
            log.warning("Info capture failed", error=str(exc))

    async def _save_console(self, page: Any, dest: Path) -> None:
        """Saves console messages if any were captured via event listener."""
        try:
            # Console messages are collected externally via page.on("console").
            # If the page exposes _console_messages (set by our code), save them.
            messages = getattr(page, "_kaio_console_messages", [])
            if messages:
                (dest / "console.log").write_text(
                    "\n".join(messages), encoding="utf-8"
                )
        except Exception as exc:
            log.warning("Console log capture failed", error=str(exc))
