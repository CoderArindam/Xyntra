"""HealthMonitor — background heartbeat for active meeting sessions.

Runs as an asyncio Task per session. Every HEARTBEAT_INTERVAL seconds:
- Checks browser context is alive
- Checks page is still open
- Updates session.last_heartbeat, browser_alive, page_alive, current_url
- If browser has died: requests cleanup via callback and stops

M1.5 additions:
- Checks intelligence observer health via ObserverSupervisor
- Requests restart of unhealthy observers (supervisor owns restart logic)
- Never restarts the browser

Never crashes the backend — all exceptions are caught and logged.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, Coroutine

from app.meeting.config import meeting_config
from app.meeting.logger import get_logger
from app.meeting.models.session import SessionStatus
from app.meeting.utils.playwright_errors import is_playwright_fatal, page_is_usable

if TYPE_CHECKING:
    from app.meeting.bot.session.manager import MeetingSessionManager
    from app.meeting.intelligence.supervisor import ObserverSupervisor

log = get_logger("session.monitor")

_OBSERVER_NAMES = (
    "speaker_detector",
    "meeting_state_observer",
)

# Type alias for the shutdown callback (session_id, reason)
ShutdownCallback = Callable[[str, str], None]


class HealthMonitor:
    """Manages per-session heartbeat asyncio tasks."""

    def __init__(self, session_manager: "MeetingSessionManager") -> None:
        self._manager = session_manager
        self._tasks: dict[str, asyncio.Task] = {}

    def start(
        self,
        session_id: str,
        controller: Any,
        page: Any,
        supervisor: "ObserverSupervisor | None" = None,
        shutdown_callback: ShutdownCallback | None = None,
        shutdown_requested: Callable[[], bool] | None = None,
    ) -> asyncio.Task:
        """Start a background heartbeat task for the given session."""
        if session_id in self._tasks:
            self.stop(session_id)

        task = asyncio.create_task(
            self._heartbeat_loop(session_id, controller, page, supervisor, shutdown_callback, shutdown_requested),
            name=f"meeting-heartbeat-{session_id[:8]}",
        )
        self._tasks[session_id] = task
        log.debug("Heartbeat started", session_id=session_id)
        return task

    def stop(self, session_id: str) -> None:
        """Cancel the heartbeat task for a session."""
        task = self._tasks.pop(session_id, None)
        if task and not task.done():
            task.cancel()
            log.debug("Heartbeat stopped", session_id=session_id)

    def stop_all(self) -> None:
        for session_id in list(self._tasks.keys()):
            self.stop(session_id)

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    async def _heartbeat_loop(
        self,
        session_id: str,
        controller: Any,
        page: Any,
        supervisor: "ObserverSupervisor | None",
        shutdown_callback: ShutdownCallback | None,
        shutdown_requested: Callable[[], bool] | None,
    ) -> None:
        while True:
            try:
                await asyncio.sleep(meeting_config.HEARTBEAT_INTERVAL)
            except asyncio.CancelledError:
                log.debug("Heartbeat cancelled during sleep", session_id=session_id)
                break

            session = self._manager.get(session_id)
            if not session or session.status in (
                SessionStatus.LEAVING,
                SessionStatus.CLEANING_UP,
                SessionStatus.FINISHED,
                SessionStatus.FAILED,
            ):
                log.debug("Heartbeat stopping — session terminal", session_id=session_id)
                break

            try:
                browser_alive = controller.is_alive()
                page_alive = browser_alive and page_is_usable(page)

                session.browser_alive = browser_alive
                session.page_alive = page_alive
                session.last_heartbeat = datetime.now(timezone.utc)

                if browser_alive:
                    try:
                        session.current_url = page.url
                    except Exception:
                        session.current_url = None

                if not browser_alive or not page_alive:
                    reason = "browser_disconnected" if not browser_alive else "page_closed"
                    log.info("health_monitor.request_cleanup", reason=reason)
                    log.warning(
                        f"{reason} — requesting shutdown",
                        session_id=session_id,
                    )
                    if shutdown_callback:
                        shutdown_callback(session_id, reason)
                    else:
                        self._manager.fail(
                            session_id,
                            f"{reason} unexpectedly",
                            "BROWSER_DISCONNECTED",
                        )
                    break

                # ── M1.5: Check intelligence observer health ─────── #
                if supervisor and browser_alive:
                    if shutdown_requested and shutdown_requested():
                        log.info("health_monitor.shutdown_detected", session_id=session_id)
                        log.info("health_monitor.stopping", session_id=session_id)
                        break
                    await self._check_observer_health(session_id, supervisor, shutdown_requested)
                    session.observer_health = supervisor.get_health()
                    session.intelligence_alive = all(
                        supervisor.is_observer_healthy(name)
                        for name in _OBSERVER_NAMES
                    )

            except asyncio.CancelledError:
                log.debug("Heartbeat cancelled", session_id=session_id)
                break
            except Exception as exc:
                if is_playwright_fatal(exc):
                    log.info("Heartbeat — browser gone, requesting shutdown", session_id=session_id)
                    if shutdown_callback:
                        shutdown_callback(session_id, "playwright_fatal_error")
                    break
                log.warning(
                    "Heartbeat tick error",
                    session_id=session_id,
                    error=str(exc),
                )

    async def _check_observer_health(
        self,
        session_id: str,
        supervisor: "ObserverSupervisor",
        shutdown_requested: Callable[[], bool] | None,
    ) -> None:
        """Ask the supervisor to restart any unhealthy observer.

        HealthMonitor reports — Supervisor decides and restarts.
        This never restarts the browser or affects other observers.
        """
        for name in _OBSERVER_NAMES:
            if not supervisor.is_observer_healthy(name):
                log.info("health_monitor.restart_observer", observer=name, reason="unhealthy")
                log.warning(
                    "Observer unhealthy — requesting restart",
                    name=name,
                    session_id=session_id,
                )
                if shutdown_requested and shutdown_requested():
                    log.info("health_monitor.shutdown_detected", session_id=session_id)
                    log.info("health_monitor.restart_skipped", name=name, session_id=session_id)
                    return
                restarted = await supervisor.restart_observer(name)
                if not restarted:
                    log.error(
                        "Observer restart failed or capped",
                        name=name,
                        session_id=session_id,
                    )
