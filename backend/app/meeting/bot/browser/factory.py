"""BrowserFactory — centralized browser creation and extension loading.

Responsibilities:
- Resolve and validate extension directory
- Construct Chromium arguments
- Launch persistent Playwright context
- Verify extension successfully loaded (not just present on disk)
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from app.meeting.bot.browser.models import BrowserSession
from app.meeting.config import meeting_config
from app.meeting.exceptions import BrowserLaunchError
from app.meeting.logger import get_logger

log = get_logger("browser.factory")

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


class BrowserFactory:
    """Creates a fully configured BrowserSession using Playwright."""

    @classmethod
    def resolve_extension_path(cls) -> Path | None:
        """Dynamically resolve the configured extension directory."""
        if not meeting_config.EXTENSION_ENABLED:
            return None

        configured_path = Path(meeting_config.EXTENSION_DIRECTORY)
        if configured_path.is_absolute():
            candidate = configured_path
        else:
            # Try relative to backend root (assuming factory is in app/meeting/bot/browser/factory.py)
            backend_root = Path(__file__).resolve().parents[4]
            candidate = backend_root / configured_path
            
            # If not found, try from current working directory
            if not candidate.exists():
                candidate = Path.cwd() / configured_path
                
        if not candidate.exists():
            raise BrowserLaunchError(
                f"Extension directory not found: {candidate}", retryable=False
            )
            
        return candidate.resolve()

    @classmethod
    def validate_extension(cls, ext_path: Path) -> None:
        """Validate required files exist in the extension directory."""
        required_files = [
            "manifest.json",
            "background/service_worker.js",
            "content/meet_observer.js",
        ]
        
        for rel_path in required_files:
            file_path = ext_path / rel_path
            if not file_path.exists():
                raise BrowserLaunchError(
                    f"Invalid extension at {ext_path}: missing '{rel_path}'",
                    retryable=False,
                )

    @classmethod
    async def _wait_for_extension(cls, context: Any, timeout: float = 5.0) -> Any:
        """Wait for the extension's service worker to load and return it.
        
        Chromium MV3 extensions load a background service worker. We poll the
        Playwright context's service_workers list until it appears.
        """
        import time
        start_time = time.time()
        while time.time() - start_time < timeout:
            if context.service_workers:
                return context.service_workers[0]
            # Also check background pages for MV2 compatibility or side panels
            if context.background_pages:
                return context.background_pages[0]
            await asyncio.sleep(0.1)
        return None

    @classmethod
    async def verify_service_worker(cls, context: Any) -> None:
        """Verify the service worker is active, unique, and responds to ping."""
        workers = context.service_workers
        
        if len(workers) == 0:
            raise BrowserLaunchError("Extension Service Worker failed to start.", retryable=False)
        if len(workers) > 1:
            raise BrowserLaunchError(f"Duplicate Service Workers detected ({len(workers)}). Expected exactly 1.", retryable=False)
            
        worker = workers[0]
        
        try:
            # Perform a runtime check of the Service Worker state
            pong = await worker.evaluate(
                '''() => {
                    return {
                        type: "PONG",
                        extension_version: chrome.runtime.getManifest().version,
                        manifest_version: chrome.runtime.getManifest().manifest_version,
                        active_tabs: typeof activeTabs !== "undefined" ? activeTabs : {}
                    };
                }'''
            )
            
            if not pong or pong.get("type") != "PONG":
                raise BrowserLaunchError(
                    f"Service Worker handshake failed. Unexpected response: {pong}",
                    retryable=False
                )
                
            log.info("Service worker verified", version=pong.get("extension_version"))
            
        except Exception as e:
            if isinstance(e, BrowserLaunchError):
                raise
            raise BrowserLaunchError(f"Error communicating with Service Worker: {e}", retryable=False)

    @classmethod
    async def create(
        cls,
        profile_dir: str,
        *,
        headless: bool = True,
        page_timeout: int = 30_000,
    ) -> BrowserSession:
        """Launch a persistent Playwright context with the extension preloaded."""
        try:
            # pyrefly: ignore [missing-import]
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise BrowserLaunchError(
                "Playwright is not installed. "
                "Run: pip install playwright && playwright install chromium",
                retryable=False,
            ) from exc

        ext_path = cls.resolve_extension_path()
        args = list(_CHROMIUM_ARGS)
        
        if ext_path:
            cls.validate_extension(ext_path)
            args.append(f"--disable-extensions-except={ext_path}")
            args.append(f"--load-extension={ext_path}")
            log.info("Extension validated", path=str(ext_path))
        else:
            log.info("Extension Disabled By Configuration")

        Path(profile_dir).mkdir(parents=True, exist_ok=True)
        
        playwright_instance = None
        context = None
        
        try:
            playwright_instance = await async_playwright().start()
            
            # Note: headless=True restricts extensions in standard chromium. 
            # In playwright, to load extension in headless, you might need to use headless="new" or False.
            # But recent playwright versions handle it if you just pass the extension args, though headless=False is often safer.
            
            context = await playwright_instance.chromium.launch_persistent_context(
                profile_dir,
                headless=headless,
                args=args,
                ignore_default_args=_IGNORE_ARGS,
                permissions=["camera", "microphone"],
                viewport={"width": 1280, "height": 800},
            )
            
            context.set_default_timeout(page_timeout)
            
            extension_loaded = False
            if ext_path:
                worker = await cls._wait_for_extension(context)
                if not worker:
                    raise BrowserLaunchError(
                        "Chromium launched but extension service worker failed to load within timeout.",
                        retryable=False,
                    )
                
                await cls.verify_service_worker(context)
                
                # Configure the extension
                await worker.evaluate(f'''async () => {{
                    await chrome.storage.local.set({{
                        backendUrl: "http://127.0.0.1:8000/api/v1",
                        apiKey: "dev-key"
                    }});
                    // Update variables directly in scope and trigger registration
                    backendUrl = "http://127.0.0.1:8000/api/v1";
                    apiKey = "dev-key";
                    if (typeof registerWithBackend === "function") {{
                        registerWithBackend();
                    }}
                }}''')
                
                extension_loaded = True
                log.info("Extension Loaded and Verified Successfully")
                
            return BrowserSession(
                playwright=playwright_instance,
                context=context,
                profile_path=Path(profile_dir),
                extension_loaded=extension_loaded,
            )
            
        except Exception as exc:
            log.error("Browser launch failed", error=str(exc))
            if context:
                await context.close()
            if playwright_instance:
                await playwright_instance.stop()
            
            if isinstance(exc, BrowserLaunchError):
                raise
            raise BrowserLaunchError(f"Failed to launch browser: {exc}") from exc
