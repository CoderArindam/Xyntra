"""GoogleMeetJoiner — handles the Google Meet join flow.

Responsibilities:
- Navigate to a Meet URL
- Dismiss cookie banners
- Disable microphone and camera (pre-join lobby)
- Set bot display name if required
- Click Join / Ask to Join
- Detect and return the resulting JoinState

All DOM selectors live in utils/google_selectors.py.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.meeting.exceptions import MeetingJoinError, NetworkError, PermissionDeniedError
from app.meeting.logger import get_logger
from app.meeting.models.session import JoinState
from app.meeting.utils.google_selectors import MEET_SELECTORS as SEL

log = get_logger("bot.joiner")

_NAV_TIMEOUT = 30_000       # ms — page navigation
_ELEMENT_TIMEOUT = 10_000   # ms — waiting for elements
_JOIN_POLL_INTERVAL = 1.0   # seconds between polls
_JOIN_CONFIRM_SECS = 30     # seconds — primary polling window
_JOIN_RECHECK_SECS = 5      # seconds — secondary verification window
_JOIN_MIN_CONFIDENCE = 3    # indicators required to confirm join


class GoogleMeetJoiner:
    """Joins and leaves Google Meet sessions via Playwright.

    Has no knowledge of sessions, config, or orchestration — only page
    automation. The caller is responsible for providing an authenticated
    Playwright Page.
    """

    # ------------------------------------------------------------------ #
    # Public                                                               #
    # ------------------------------------------------------------------ #

    async def join(self, page: Any, meeting_url: str, bot_name: str = "") -> JoinState:
        """Join a Google Meet session.

        Returns:
            JoinState describing the outcome (IN_MEETING, WAITING_FOR_ADMISSION,
            or an error state).
        """
        log.info("meeting.join.start", url=meeting_url)

        try:
            await self._navigate(page, meeting_url)
            await self._dismiss_cookie_banner(page)
            join_state = await self._detect_early_errors(page)
            if join_state is not None:
                return join_state

            await self._disable_microphone(page)
            await self._disable_camera(page)
            if bot_name:
                await self._set_display_name(page, bot_name)

            return await self._click_join_and_detect(page)

        except (MeetingJoinError, NetworkError, PermissionDeniedError):
            raise
        except Exception as exc:
            log.error("meeting.join.failed", error=str(exc), url=meeting_url)
            return JoinState.UNKNOWN_ERROR

    async def leave(self, page: Any) -> None:
        """Leave the current meeting — click Leave button or close the page."""
        log.info("meeting.session.closed — attempting graceful leave")
        try:
            leave_btn = page.locator(SEL["leave_btn"])
            if await leave_btn.count() > 0:
                await leave_btn.first.click()
                await asyncio.sleep(1)
                log.info("meeting.session.closed — clicked leave button")
                return
        except Exception:
            pass

        # Fallback — close the page directly
        try:
            await page.close()
            log.info("meeting.session.closed — page closed (fallback)")
        except Exception as exc:
            log.warning("Leave fallback page.close() failed", error=str(exc))

    # ------------------------------------------------------------------ #
    # Navigation                                                           #
    # ------------------------------------------------------------------ #

    async def _navigate(self, page: Any, url: str) -> None:
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=_NAV_TIMEOUT)
            await page.wait_for_load_state("networkidle", timeout=_NAV_TIMEOUT)
        except Exception as exc:
            raise NetworkError(f"Failed to navigate to meeting URL: {exc}") from exc

    # ------------------------------------------------------------------ #
    # Cookie banner                                                        #
    # ------------------------------------------------------------------ #

    async def _dismiss_cookie_banner(self, page: Any) -> None:
        for selector_key in ("cookie_accept_all", "cookie_accept", "cookie_reject_all"):
            try:
                btn = page.locator(SEL[selector_key])
                if await btn.count() > 0:
                    await btn.first.click()
                    log.debug("Dismissed cookie banner", selector=selector_key)
                    await asyncio.sleep(0.5)
                    return
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    # Early error detection                                                #
    # ------------------------------------------------------------------ #

    async def _detect_early_errors(self, page: Any) -> JoinState | None:
        error_map = {
            "meeting_not_found": JoinState.MEETING_NOT_FOUND,
            "meeting_ended": JoinState.MEETING_ENDED,
            "permission_denied": JoinState.PERMISSION_DENIED,
            "login_required": JoinState.LOGIN_REQUIRED,
        }
        for selector_key, state in error_map.items():
            try:
                elem = page.locator(SEL[selector_key])
                if await elem.count() > 0:
                    log.warning("meeting.join.failed — early error detected", state=state)
                    return state
            except Exception:
                pass
        return None

    # ------------------------------------------------------------------ #
    # Pre-join controls                                                    #
    # ------------------------------------------------------------------ #

    async def _disable_microphone(self, page: Any) -> None:
        """Turn off mic if it is currently on."""
        try:
            # The button label is "Turn off microphone" only when mic is ON
            mic_on_btn = page.locator(SEL["mic_toggle"])
            if await mic_on_btn.count() > 0:
                await mic_on_btn.first.click()
                log.debug("Microphone disabled")
        except Exception as exc:
            log.warning("Could not disable microphone", error=str(exc))

    async def _disable_camera(self, page: Any) -> None:
        """Turn off camera if it is currently on."""
        try:
            cam_on_btn = page.locator(SEL["cam_toggle"])
            if await cam_on_btn.count() > 0:
                await cam_on_btn.first.click()
                log.debug("Camera disabled")
        except Exception as exc:
            log.warning("Could not disable camera", error=str(exc))

    async def _set_display_name(self, page: Any, name: str) -> None:
        """Fill the display name field if visible."""
        try:
            name_input = page.locator(SEL["name_input"])
            if await name_input.count() > 0:
                await name_input.clear()
                await name_input.fill(name)
                log.debug("Display name set", name=name)
        except Exception as exc:
            log.warning("Could not set display name", error=str(exc))

    # ------------------------------------------------------------------ #
    # Join & state detection                                               #
    # ------------------------------------------------------------------ #

    async def _click_join_and_detect(self, page: Any) -> JoinState:
        """Click the join button (whichever is present) and detect the outcome."""

        # Try "Join now" first, then "Ask to join" (waiting room flow)
        clicked = await self._try_click_join_now(page) or await self._try_click_ask_to_join(page)

        if not clicked:
            log.warning("meeting.join.failed — no join button found")
            return JoinState.UNKNOWN_ERROR

        # Wait for confirmation: in-meeting controls or waiting room text
        return await self._wait_for_join_result(page)

    async def _try_click_join_now(self, page: Any) -> bool:
        for selector_key in ("join_now_btn", "join_now_jsname"):
            try:
                btn = page.locator(SEL[selector_key])
                if await btn.count() > 0:
                    await btn.first.click()
                    log.info("meeting.join.joining — clicked 'Join now'")
                    return True
            except Exception:
                pass
        return False

    async def _try_click_ask_to_join(self, page: Any) -> bool:
        try:
            btn = page.locator(SEL["ask_to_join_btn"])
            if await btn.count() > 0:
                await btn.first.click()
                log.info("meeting.join.waiting — clicked 'Ask to join'")
                return True
        except Exception:
            pass
        return False

    # Ordered list of (selector_key, human-readable label)
    _JOIN_INDICATORS = [
        ("indicator_leave",        "Leave button"),
        ("indicator_mic",          "Mic button"),
        ("indicator_camera",       "Camera button"),
        ("indicator_more_options", "More options button"),
        ("indicator_people",       "People button"),
        ("indicator_chat",         "Chat button"),
        ("indicator_activities",   "Activities button"),
        ("indicator_toolbar",      "Bottom toolbar"),
        ("indicator_captions",     "Captions button"),
        ("indicator_timer",        "Meeting timer"),
    ]

    async def _wait_for_join_result(self, page: Any) -> JoinState:
        """Poll for in-meeting state or waiting room over _JOIN_CONFIRM_SECS.

        Uses a confidence model: counts how many independent in-meeting
        indicators are visible.  >=_JOIN_MIN_CONFIDENCE  -> IN_MEETING.
        If the primary window elapses without confidence, a secondary
        5-second recheck runs before returning the final verdict.
        """
        state = await self._primary_join_poll(page)
        if state is not None:
            return state

        log.warning(
            "meeting.join.inconclusive — starting secondary verification",
            recheck_secs=_JOIN_RECHECK_SECS,
        )
        await asyncio.sleep(_JOIN_RECHECK_SECS)
        return await self._secondary_join_verification(page)

    # ------------------------------------------------------------------ #
    # Join polling helpers                                                 #
    # ------------------------------------------------------------------ #

    async def _primary_join_poll(self, page: Any) -> JoinState | None:
        """Poll every second for _JOIN_CONFIRM_SECS.

        Returns a JoinState immediately when a clear signal is found,
        or None to signal that the secondary verification pass should run.
        """
        deadline = asyncio.get_event_loop().time() + _JOIN_CONFIRM_SECS

        while asyncio.get_event_loop().time() < deadline:
            # Waiting room takes priority — it's a clean known state
            for selector_key in ("waiting_room_text", "waiting_for_host"):
                try:
                    if await page.locator(SEL[selector_key]).count() > 0:
                        log.info("meeting.join.waiting — in waiting room")
                        return JoinState.WAITING_FOR_ADMISSION
                except Exception:
                    pass

            # Check for post-click error banners
            post_join_errors = {
                "meeting_not_found": JoinState.MEETING_NOT_FOUND,
                "meeting_ended":     JoinState.MEETING_ENDED,
                "permission_denied": JoinState.PERMISSION_DENIED,
                "network_error":     JoinState.NETWORK_FAILURE,
            }
            for selector_key, error_state in post_join_errors.items():
                try:
                    if await page.locator(SEL[selector_key]).count() > 0:
                        log.warning("meeting.join.error_detected", state=error_state)
                        return error_state
                except Exception:
                    pass

            # Confidence check across all in-meeting indicators
            confidence, detected = await self._check_join_indicators(page)
            self._log_indicators(detected, confidence)

            if confidence >= _JOIN_MIN_CONFIDENCE:
                log.info(
                    "meeting.join.confirmed",
                    confidence=f"{confidence}/{len(self._JOIN_INDICATORS)}",
                )
                return JoinState.IN_MEETING

            await asyncio.sleep(_JOIN_POLL_INTERVAL)

        return None  # inconclusive — trigger secondary pass

    async def _secondary_join_verification(self, page: Any) -> JoinState:
        """Last-resort check after the primary window expires.

        Verifies URL + a fresh confidence snapshot before giving up.
        Only returns UNKNOWN_ERROR if absolutely nothing confirms the join.
        """
        try:
            url = page.url
        except Exception:
            url = ""

        url_ok = "meet.google.com" in url
        confidence, detected = await self._check_join_indicators(page)
        self._log_indicators(detected, confidence)

        # URL alone isn't enough, but combined with any indicator it is
        effective_confidence = confidence + (1 if url_ok else 0)

        if effective_confidence >= _JOIN_MIN_CONFIDENCE:
            log.info(
                "meeting.join.confirmed_by_secondary",
                url=url,
                confidence=f"{effective_confidence}/{len(self._JOIN_INDICATORS) + 1}",
            )
            return JoinState.IN_MEETING

        # Still in a Google Meet URL but < threshold — treat as joined
        # rather than kill the browser; HealthMonitor will take over.
        if url_ok and confidence >= 1:
            log.warning(
                "meeting.join.low_confidence_accepted",
                url=url,
                confidence=f"{confidence}/{len(self._JOIN_INDICATORS)}",
                reason="URL is meet.google.com and at least one control visible",
            )
            return JoinState.IN_MEETING

        log.warning(
            "meeting.join.failed — all verification passes exhausted",
            url=url,
            confidence=f"{confidence}/{len(self._JOIN_INDICATORS)}",
        )
        return JoinState.UNKNOWN_ERROR

    async def _check_join_indicators(
        self,
        page: Any,
    ) -> tuple[int, dict[str, bool]]:
        """Check all join indicators and return (confidence_score, detected_map)."""
        detected: dict[str, bool] = {}
        for key, label in self._JOIN_INDICATORS:
            try:
                found = await page.locator(SEL[key]).count() > 0
            except Exception:
                found = False
            detected[label] = found
        confidence = sum(1 for v in detected.values() if v)
        return confidence, detected

    def _log_indicators(self, detected: dict[str, bool], confidence: int) -> None:
        """Emit a structured log entry showing which indicators were seen."""
        lines = [
            f"  {'\u2713' if ok else '\u2717'} {label}"
            for label, ok in detected.items()
        ]
        summary = "\n".join(lines)
        log.debug(
            "Join indicators",
            indicators=summary,
            confidence=confidence,
            total=len(self._JOIN_INDICATORS),
        )
