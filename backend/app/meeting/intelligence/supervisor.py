"""ObserverSupervisor — owns the full lifecycle of all intelligence observers.

Design:
  - HealthMonitor reports observer failures; Supervisor decides to restart.
  - Each observer can be restarted independently without affecting others or the browser.
  - Restart cap (_MAX_RESTARTS) prevents infinite-loop restarts.
"""

from __future__ import annotations

from typing import Any

from app.meeting.intelligence.base import BaseObserver
from app.meeting.intelligence.context import MeetingContext
from app.meeting.intelligence.meeting_state import MeetingStateObserver
from app.meeting.intelligence.models import (
    EventCategory,
    EventType,
    MeetingEvent,
)
from app.meeting.intelligence.speaker_detector import SpeakerDetector
from app.meeting.logger import get_logger

log = get_logger("intelligence.supervisor")

_MAX_RESTARTS = 5


class ObserverSupervisor:
    """Manages start/stop/restart of all three intelligence observers.

    Observers are independent: restarting one never affects the others.
    """

    def __init__(self) -> None:
        self._ctx: MeetingContext | None = None
        self._observers: dict[str, BaseObserver] = {
            "speaker_detector": SpeakerDetector(),
            "meeting_state_observer": MeetingStateObserver(),
        }

    # ------------------------------------------------------------------ #
    # Typed accessors                                                      #
    # ------------------------------------------------------------------ #

    @property
    def speaker_detector(self) -> SpeakerDetector:
        return self._observers["speaker_detector"]  # type: ignore[return-value]

    @property
    def meeting_state_observer(self) -> MeetingStateObserver:
        return self._observers["meeting_state_observer"]  # type: ignore[return-value]

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    async def start_all(self, ctx: MeetingContext) -> dict[str, Any]:
        """Start all observers and return their asyncio.Tasks.

        Per-observer failures are logged, not raised.
        """
        self._ctx = ctx
        tasks: dict[str, Any] = {}
        for name, observer in self._observers.items():
            try:
                await observer.start(ctx)
                if observer._task:
                    tasks[name] = observer._task
                log.info("observer.started", name=name, session_id=ctx.session_id)
            except Exception as exc:
                log.error(
                    "observer.start_failed",
                    name=name,
                    session_id=ctx.session_id,
                    error=str(exc),
                )
        return tasks

    async def stop_all(self) -> None:
        """Stop all observers. Per-observer failures are logged, not raised."""
        sid = self._ctx.session_id if self._ctx else "unknown"
        for name, observer in self._observers.items():
            try:
                await observer.stop()
                log.info("observer.stopped", name=name, session_id=sid)
            except Exception as exc:
                log.warning("observer.stop_error", name=name, error=str(exc))

    async def restart_observer(self, name: str) -> bool:
        """Restart a single observer. Returns True on success.

        Will not restart if the observer has already been restarted _MAX_RESTARTS times.
        Never touches the browser or other observers.
        """
        observer = self._observers.get(name)
        if not observer or not self._ctx:
            log.warning("restart_observer called for unknown observer", name=name)
            return False

        metrics = observer.get_metrics()
        if metrics.restart_count >= _MAX_RESTARTS:
            log.error(
                "observer.max_restarts_exceeded",
                name=name,
                session_id=self._ctx.session_id,
                restart_count=metrics.restart_count,
            )
            return False

        try:
            await observer.stop()
            metrics.restart_count += 1
            await observer.start(self._ctx)

            log.info(
                "observer.restarted",
                name=name,
                session_id=self._ctx.session_id,
                restart_count=metrics.restart_count,
            )

            await self._ctx.event_bus.emit(
                MeetingEvent(
                    type=EventType.OBSERVER_RESTARTED,
                    category=EventCategory.SYSTEM,
                    source="supervisor",
                    payload={
                        "observer": name,
                        "restart_count": metrics.restart_count,
                    },
                )
            )
            return True

        except Exception as exc:
            log.error(
                "observer.restart_failed",
                name=name,
                session_id=self._ctx.session_id,
                error=str(exc),
            )
            return False

    # ------------------------------------------------------------------ #
    # Health                                                               #
    # ------------------------------------------------------------------ #

    def is_observer_healthy(self, name: str) -> bool:
        observer = self._observers.get(name)
        if not observer:
            return False
        return observer.is_running() and observer.get_metrics().healthy

    def get_health(self) -> dict[str, Any]:
        """Return per-observer metrics dict for HealthMonitor and API."""
        return {
            name: observer.get_metrics().to_dict()
            for name, observer in self._observers.items()
        }
