"""GoogleAuthService — persistent Google authentication via Playwright.

Detects whether the browser profile already has a valid Google session.
If yes, skips login entirely. If not, runs the standard email→password
flow and waits for session persistence.

All DOM selectors are imported from utils/google_selectors.py — change
Google's UI in one place only.
"""

from __future__ import annotations

import asyncio
import time
import tempfile
from enum import Enum, auto
from pathlib import Path
from typing import Any

from app.meeting.exceptions import AuthenticationError
from app.meeting.logger import get_logger
from app.meeting.utils.google_selectors import (
    GOOGLE_ACCOUNT_URL,
    GOOGLE_MY_ACCOUNT_URL,
    GOOGLE_AUTH_SELECTORS as SEL,
)

log = get_logger("browser.auth")

_AUTH_CHECK_TIMEOUT = 15_000   # ms — how long to wait for redirect on auth check
_LOGIN_STEP_TIMEOUT = 20_000   # ms — timeout per login step
_POST_LOGIN_TIMEOUT = 30_000   # ms — wait for final redirect after password


class AuthState(Enum):
    UNKNOWN = auto()
    EMAIL = auto()
    PASSWORD = auto()
    ACCOUNT_CHOOSER = auto()
    CONSENT = auto()
    TWO_FACTOR = auto()
    AUTHENTICATED = auto()
    ERROR = auto()
    VERIFY_ITS_YOU = auto()


class GoogleAuthService:
    """Handles Google account authentication for the meeting bot.

    Designed so that:
    - First run: performs full email + password login, profile persists session.
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

        if await self._is_authenticated(page):
            log.info("meeting.auth.cached — reusing persisted session")
            return

        log.info("meeting.auth.login — no cached session, starting login flow")
        await self._perform_login(page)
        log.info("meeting.auth.success")

    async def _is_authenticated(self, page: Any) -> bool:
        """Navigate to Google Accounts and check if we're already signed in."""
        try:
            await page.goto(GOOGLE_ACCOUNT_URL, wait_until="domcontentloaded", timeout=_AUTH_CHECK_TIMEOUT)
            await page.wait_for_load_state("networkidle", timeout=_AUTH_CHECK_TIMEOUT)
        except Exception:
            return False

        current_url = page.url
        return GOOGLE_MY_ACCOUNT_URL in current_url or "meet.google.com" in current_url

    async def _perform_login(self, page: Any) -> None:
        try:
            await self._navigate_to_signin(page)
            
            # Using max_steps to prevent an infinite loop while still using while True pattern
            max_steps = 15
            step = 0
            previous_state = None
            
            while step < max_steps:
                state = await self.detect_login_state(page)
                
                # Log state transitions
                if previous_state and previous_state != state and state != AuthState.UNKNOWN:
                    log.info(f"{previous_state.name} \u2192 {state.name}")
                if state != AuthState.UNKNOWN:
                    previous_state = state
                
                match state:
                    case AuthState.EMAIL:
                        await self._handle_email(page)
                        await self._wait_for_transition(page, state)
                        
                    case AuthState.PASSWORD:
                        await self._handle_password(page)
                        await self._wait_for_transition(page, state)
                        
                    case AuthState.ACCOUNT_CHOOSER:
                        await self._handle_account_selection(page)
                        await self._wait_for_transition(page, state)
                        
                    case AuthState.CONSENT:
                        await self._handle_consent(page)
                        await self._wait_for_transition(page, state)
                        
                    case AuthState.VERIFY_ITS_YOU:
                        await self._handle_verify_its_you(page)
                        await self._wait_for_transition(page, state)
                        
                    case AuthState.TWO_FACTOR:
                        raise AuthenticationError("Two-factor authentication required. Please disable 2FA for this bot account.", retryable=False)
                        
                    case AuthState.AUTHENTICATED:
                        log.info("Successfully authenticated via state machine.")
                        return
                        
                    case AuthState.ERROR:
                        raise AuthenticationError("Google rejected the credentials or blocked the login.", retryable=False)
                        
                    case AuthState.UNKNOWN:
                        await self._capture_debug(page, state)
                        # Wait a bit before retry_detection in the next loop tick
                        await asyncio.sleep(2)
                        
                step += 1
                
            raise AuthenticationError("Authentication flow timed out: too many steps.", retryable=False)
        except AuthenticationError:
            raise
        except Exception as exc:
            try:
                await self._capture_debug(page, AuthState.UNKNOWN)
            except Exception:
                pass
            raise AuthenticationError(f"Google login flow failed unexpectedly: {exc}", retryable=False) from exc

    async def _wait_for_transition(self, page: Any, old_state: AuthState) -> None:
        """Wait for the page state to change dynamically instead of fixed sleeps."""
        start = time.time()
        timeout = 15.0
        while time.time() - start < timeout:
            new_state = await self.detect_login_state(page)
            if new_state != old_state and new_state != AuthState.UNKNOWN:
                return
            await asyncio.sleep(0.5)

    async def detect_login_state(self, page: Any) -> AuthState:
        """Evaluate multiple independent signals to classify the current page."""
        try:
            # Quick check to avoid checking locators while network is heavily loading SPA
            await page.wait_for_load_state("networkidle", timeout=1000)
        except Exception:
            pass
            
        start_time = time.time()
        timeout = 3.0
        
        while time.time() - start_time < timeout:
            # 1. AUTHENTICATED
            if "myaccount.google.com" in page.url or "meet.google.com" in page.url:
                return AuthState.AUTHENTICATED
            if await page.locator('a[aria-label^="Google Account"]').count() > 0 and await page.locator('a[aria-label^="Google Account"]').first.is_visible():
                return AuthState.AUTHENTICATED
                
            # 2. ERROR (Invalid credentials, captcha, blocked, suspicious login)
            if await page.locator('.LXRPh').first.is_visible() or \
               await page.locator('.o6cuMc').first.is_visible() or \
               await page.locator('iframe[src*="recaptcha"]').first.is_visible() or \
               await page.get_by_text("Suspicious activity").first.is_visible():
                return AuthState.ERROR
                
            if await page.get_by_text("Verify it's you").first.is_visible():
                return AuthState.VERIFY_ITS_YOU
                
            # 3. TWO_FACTOR
            if await page.get_by_text("Verify").first.is_visible() or \
               await page.get_by_text("Security code").first.is_visible() or \
               await page.get_by_text("Check your phone").first.is_visible() or \
               await page.locator('#challengePickerList').first.is_visible():
                return AuthState.TWO_FACTOR
                
            # 4. CONSENT
            if await page.get_by_text("Continue").first.is_visible() or \
               await page.get_by_text("I agree").first.is_visible() or \
               await page.get_by_text("Review").first.is_visible() or \
               await page.get_by_text("Accept all").first.is_visible():
                return AuthState.CONSENT
                
            # 5. ACCOUNT_CHOOSER
            if await page.get_by_text("Choose an account").first.is_visible() or \
               await page.locator('[data-profileindex]').first.is_visible():
                return AuthState.ACCOUNT_CHOOSER
                
            # 6. PASSWORD (Improved robust detection)
            has_welcome = await page.get_by_text("Welcome", exact=True).first.is_visible() or \
                          await page.locator('h1:has-text("Welcome")').first.is_visible()
            has_pwd_input = await page.locator('input[type="password"]').first.is_visible() or \
                            await page.locator('input[name="Passwd"]').first.is_visible()
                            
            if "/challenge/pwd" in page.url or \
               has_pwd_input or \
               await page.get_by_label("Enter your password").first.is_visible() or \
               (has_welcome and has_pwd_input):
                return AuthState.PASSWORD
                
            # 7. EMAIL
            if await page.locator('input[type="email"]').first.is_visible() or \
               await page.locator('#identifierId').first.is_visible() or \
               await page.get_by_label("Email or phone").first.is_visible():
                return AuthState.EMAIL
                
            await asyncio.sleep(0.5)
            
        return AuthState.UNKNOWN

    async def _safe_submit(self, page: Any, input_field: Any, next_button: Any) -> None:
        """Securely submits a form overcoming Playwright pointer interceptions."""
        # 1. Try pressing Enter on the focused input.
        try:
            await input_field.press("Enter", timeout=1000)
            return
        except Exception:
            pass
            
        # 2. Press Enter via keyboard
        try:
            await page.keyboard.press("Enter")
            return
        except Exception:
            pass
            
        # 3. Only if necessary, click the Next button
        try:
            if await next_button.is_visible():
                await next_button.click(timeout=1500)
                return
        except Exception:
            pass
            
        # 4. As a final fallback use locator.click(force=True)
        try:
            if await next_button.is_visible():
                await next_button.click(force=True, timeout=1500)
        except Exception as e:
            log.warning(f"All safe_submit methods failed: {e}")

    async def _capture_debug(self, page: Any, state: AuthState) -> None:
        """Capture and log diagnostic information for robust debugging."""
        url = page.url
        title = await page.title()
        
        async def get_texts(selector: str) -> list[str]:
            locator = page.locator(selector)
            count = await locator.count()
            texts = []
            for i in range(count):
                if await locator.nth(i).is_visible():
                    text = await locator.nth(i).inner_text()
                    texts.append(text.strip().replace('\n', ' '))
            return texts
            
        async def get_input_names(selector: str) -> list[str]:
            locator = page.locator(selector)
            count = await locator.count()
            attrs = []
            for i in range(count):
                if await locator.nth(i).is_visible():
                    name = await locator.nth(i).get_attribute("name") or await locator.nth(i).get_attribute("type")
                    if name:
                        attrs.append(str(name))
            return attrs

        headings = await get_texts("h1, h2, h3")
        buttons = await get_texts('button, [role="button"]')
        inputs = await get_input_names("input")
        
        log_message = (
            f"Detected URL: {url}\n"
            f"Detected title: {title}\n"
            f"Visible inputs: {inputs}\n"
            f"Visible buttons: {buttons}\n"
            f"Visible headings: {headings}\n"
            f"Current detection state: {state.name}"
        )
        log.error(log_message)
        
        # Capture HTML and screenshot
        html = await page.content()
        log.error(f"HTML Dump (truncated): {html[:3000]}...")
        
        tmp_path = Path(tempfile.gettempdir()) / f"google_auth_failure_{int(time.time())}.png"
        await page.screenshot(path=str(tmp_path), full_page=True)
        log.error(f"Saved screenshot to: {tmp_path}")

    async def _navigate_to_signin(self, page: Any) -> None:
        await page.goto(
            "https://accounts.google.com/signin",
            wait_until="domcontentloaded",
            timeout=_LOGIN_STEP_TIMEOUT,
        )

    async def _handle_email(self, page: Any) -> None:
        # Evaluate which email input to use
        email_input = page.get_by_label("Email or phone").first
        if not await email_input.is_visible():
            email_input = page.locator('input[type="email"]').first
            if not await email_input.is_visible():
                email_input = page.locator('#identifierId').first
            
        await email_input.fill(self._email)
        
        # Click the next button, which can vary
        next_btn = page.get_by_role("button", name="Next").first
        if not await next_btn.is_visible():
            next_btn = page.get_by_text("Next", exact=True).first
            
        log.debug("Submitting email...")
        await self._safe_submit(page, email_input, next_btn)

    async def _handle_password(self, page: Any) -> None:
        password_input = page.get_by_label("Enter your password").first
        if not await password_input.is_visible():
            password_input = page.locator('input[type="password"]').first
            if not await password_input.is_visible():
                password_input = page.locator('input[name="Passwd"]').first
            
        await password_input.fill(self._password)
        
        next_btn = page.get_by_role("button", name="Next").first
        if not await next_btn.is_visible():
            next_btn = page.get_by_text("Next", exact=True).first
            
        log.debug("Submitting password...")
        await self._safe_submit(page, password_input, next_btn)

    async def _handle_account_selection(self, page: Any) -> None:
        email_loc = page.get_by_text(self._email).first
        if await email_loc.is_visible():
            await email_loc.click()
        else:
            use_another = page.get_by_text("Use another account").first
            if await use_another.is_visible():
                await use_another.click()
            else:
                await page.locator('[data-profileindex]').first.click()
        log.debug("Account chooser handled")

    async def _handle_consent(self, page: Any) -> None:
        accept_btn = page.get_by_text("Accept all").first
        if await accept_btn.is_visible():
            await accept_btn.click()
        else:
            continue_btn = page.get_by_text("Continue").first
            if await continue_btn.is_visible():
                await continue_btn.click()
            else:
                agree_btn = page.get_by_text("I agree").first
                if await agree_btn.is_visible():
                    await agree_btn.click()
                else:
                    review_btn = page.get_by_text("Review").first
                    if await review_btn.is_visible():
                        await review_btn.click()
        log.debug("Consent accepted")

    async def _handle_verify_its_you(self, page: Any) -> None:
        next_btn = page.get_by_role("button", name="Next").first
        if not await next_btn.is_visible():
            next_btn = page.get_by_text("Next", exact=True).first
            
        if await next_btn.is_visible():
            log.debug("Clicking Next on Verify it's you screen...")
            await next_btn.click()
