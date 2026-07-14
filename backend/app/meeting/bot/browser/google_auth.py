"""GoogleAuthService — persistent Google authentication via Playwright.

Detects whether the browser profile already has a valid Google session.
If yes, skips login entirely. If not, pauses and waits for manual login.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from app.meeting.exceptions import AuthenticationError
from app.meeting.logger import get_logger
from app.meeting.utils.google_selectors import (
    GOOGLE_ACCOUNT_URL,
    GOOGLE_MY_ACCOUNT_URL,
)

log = get_logger("browser.auth")

_AUTH_CHECK_TIMEOUT = 15_000   # ms — how long to wait for redirect on auth check


class GoogleAuthService:
    """Handles Google account authentication for the meeting bot.

    Designed so that:
    - First run: performs manual login, profile persists session.
    - Subsequent runs: detects cached session and skips login immediately.
    """

    def __init__(self, email: str, password: str) -> None:
        if not email or not password:
            raise AuthenticationError(
                "MEETING_GOOGLE_EMAIL and MEETING_GOOGLE_PASSWORD must be set in .env",
                retryable=False,
            )
        self._email = email
        self._password = password

    async def ensure_authenticated(self, page: Any) -> None:
        """Guarantee the page is authenticated with Google."""
        log.info("meeting.auth.start")
        log.info("browser.profile_loaded")

        if await self._is_authenticated(page):
            log.info("meeting.auth.cached — reusing persisted session")
            log.info("browser.profile_reused")
            return

        log.info("meeting.auth.login — no cached session, starting login flow")
        log.info("browser.authentication_required")
        await self._perform_login(page)
        log.info("meeting.auth.success")
        log.info("browser.authentication_completed")

    async def _is_authenticated(self, page: Any) -> bool:
        """Navigate to Google Accounts and check if we're already signed in."""
        try:
            await page.goto(GOOGLE_ACCOUNT_URL, wait_until="domcontentloaded", timeout=_AUTH_CHECK_TIMEOUT)
            await page.wait_for_load_state("networkidle", timeout=_AUTH_CHECK_TIMEOUT)
        except Exception:
            pass

        current_url = page.url
        return GOOGLE_MY_ACCOUNT_URL in current_url or "meet.google.com" in current_url

    async def _perform_login(self, page: Any) -> None:
        try:
            await page.goto(
                "https://accounts.google.com/signin",
                wait_until="domcontentloaded",
                timeout=_AUTH_CHECK_TIMEOUT,
            )
            
            print(
                "====================================================\n"
                "Manual Google authentication required.\n"
                "Complete the login manually in the opened browser.\n"
                "Automation is paused.\n"
                "===================================================="
            )
            
            # Wait until authentication is complete
            start_time = time.time()
            timeout = 300  # 5 minutes for manual login
            while time.time() - start_time < timeout:
                if await self._is_authenticated(page):
                    return
                await asyncio.sleep(2)
                
            raise AuthenticationError("Manual authentication timed out after 5 minutes.", retryable=False)
                
        except AuthenticationError:
            raise
        except Exception as exc:
            raise AuthenticationError(f"Google login flow failed unexpectedly: {exc}", retryable=False) from exc
