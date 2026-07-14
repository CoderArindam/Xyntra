"""BrowserController — Playwright persistent-context browser abstraction.

Exposes only high-level operations. Raw Playwright objects never escape
this class into the rest of the meeting module — only Page is passed
around (accepted as a necessary Playwright coupling for DOM interaction).

Responsibilities:
- Launch / reuse persistent Chromium profile
- Create new pages
- Alive-check
- Screenshot capture
- Graceful close / cleanup
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.meeting.exceptions import BrowserLaunchError
from app.meeting.logger import get_logger

log = get_logger("browser.controller")

# Browser launch arguments that improve bot stability and stealth
_CHROMIUM_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-blink-features=AutomationControlled",
    "--use-fake-ui-for-media-stream",   # auto-grants mic/camera prompts
    "--disable-infobars",
    "--disable-notifications",
    "--start-maximized",
]

_IGNORE_ARGS = [
    "--enable-automation",
]


class BrowserController:
    """High-level Playwright browser controller using a persistent profile.

    Lifecycle::

        ctrl = BrowserController()
        await ctrl.launch_persistent(profile_dir="/path/to/profile")
        page = await ctrl.new_page()
        ...
        await ctrl.close()
    """

    def __init__(self) -> None:
        self._playwright: Any = None
        self._context: Any = None   # BrowserContext (persistent)
        self._page: Any = None      # Active page
        self._profile_dir: str | None = None

    @property
    def is_closed(self) -> bool:
        """Return True if all Playwright resources have been cleanly released."""
        return self._page is None and self._context is None and self._playwright is None

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    async def launch_persistent(
        self,
        profile_dir: str,
        *,
        headless: bool = True,
        page_timeout: int = 30_000,
    ) -> None:
        """Start Playwright and launch a Chromium persistent-context browser.

        Args:
            profile_dir: Path to the Chromium user-data directory.
            headless: Run headless (False required for first Google login).
            page_timeout: Default timeout for all page operations (ms).

        Raises:
            BrowserLaunchError: If Playwright is not installed or launch fails.
        """
        try:
            # pyrefly: ignore [missing-import]
            from playwright.async_api import async_playwright  # lazy import
        except ImportError as exc:
            raise BrowserLaunchError(
                "Playwright is not installed. "
                "Run: pip install playwright && playwright install chromium",
                retryable=False,
            ) from exc

        Path(profile_dir).mkdir(parents=True, exist_ok=True)
        self._profile_dir = profile_dir

        try:
            self._playwright = await async_playwright().start()
            log.info(
                "browser.launch_started",
                headless=headless,
                profile=profile_dir,
            )
            self._context = await self._playwright.chromium.launch_persistent_context(
                profile_dir,
                headless=headless,
                args=_CHROMIUM_ARGS,
                ignore_default_args=_IGNORE_ARGS,
                permissions=["camera", "microphone"],
                viewport={"width": 1280, "height": 800},
            )
            # Apply default timeout to all future operations on this context
            self._context.set_default_timeout(page_timeout)
            log.info(
                "browser.launch_completed",
                headless=headless,
                profile=profile_dir,
            )
        except Exception as exc:
            await self.close()
            raise BrowserLaunchError(f"Failed to launch browser: {exc}") from exc

    async def new_page(self) -> Any:
        """Return an active page, reusing the existing one if available.

        The persistent context typically opens with one blank page. We reuse
        it rather than creating extras to avoid memory leaks.
        """
        if self._context is None:
            raise BrowserLaunchError(
                "Browser has not been launched. Call launch_persistent() first.",
                retryable=False,
            )
        pages = self._context.pages
        if pages:
            self._page = pages[0]
        else:
            self._page = await self._context.new_page()

        # Attach a console message collector to the page for debug capture
        self._page._kaio_console_messages: list[str] = []
        self._page.on(
            "console",
            lambda msg: self._page._kaio_console_messages.append(
                f"[{msg.type}] {msg.text}"
            ),
        )

        log.debug("Page ready", url=self._page.url)
        return self._page

    async def close(self) -> None:
        """Gracefully close the browser and stop Playwright in a deterministic sequence."""
        import asyncio
        
        try:
            if self._page is not None:
                await self._page.close()
        except Exception as exc:
            log.warning("browser.page_close_error", error=str(exc))

        try:
            if self._context is not None:
                await self._context.close()
        except Exception as exc:
            log.warning("browser.context_close_error", error=str(exc))

        try:
            if self._playwright is not None:
                await self._playwright.stop()
        except Exception as exc:
            log.warning("browser.playwright_stop_error", error=str(exc))

        self._page = None
        self._context = None
        self._playwright = None

        await asyncio.sleep(0.5)
        
        log.info("Browser closed", profile=self._profile_dir)

    # ------------------------------------------------------------------ #
    # Inspection                                                           #
    # ------------------------------------------------------------------ #

    def get_page(self) -> Any:
        """Return the currently active page (may be None if not started)."""
        return self._page

    def is_alive(self) -> bool:
        """Return True if the browser context is still open and reachable."""
        if self._context is None:
            return False
        try:
            # Accessing .pages raises if the context has been closed
            _ = self._context.pages
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    # Capture                                                              #
    # ------------------------------------------------------------------ #

    async def screenshot(self, path: str) -> None:
        """Save a full-page screenshot to the given path."""
        if self._page is None:
            log.warning("screenshot() called but no page is open")
            return
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            await self._page.screenshot(path=path, full_page=True)
            log.debug("Screenshot saved", path=path)
        except Exception as exc:
            log.warning("Screenshot failed", error=str(exc))

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    # Internal functions removed in favor of deterministic close
