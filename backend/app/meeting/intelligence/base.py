"""BaseObserver — common lifecycle, metrics, and error handling for all observers."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from app.meeting.intelligence.models import ObserverMetrics
from app.meeting.utils.playwright_errors import is_playwright_fatal, page_is_usable
from app.meeting.logger import get_logger

log = get_logger("intelligence.base")


class BaseObserver(ABC):
    """Shared lifecycle contract for ParticipantTracker, SpeakerDetector, and MeetingStateObserver.

    Subclasses implement `_run()` as their polling loop.
    All metrics are maintained here; subclasses call _mark_poll/_mark_success/_mark_error.
    """

    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._metrics = ObserverMetrics()
        self._page = None  # set via start(ctx)

    # ------------------------------------------------------------------ #
    # Identity                                                             #
    # ------------------------------------------------------------------ #

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable identifier used by the supervisor."""
        ...

    # ------------------------------------------------------------------ #
    # Polling loop — implemented by each observer                         #
    # ------------------------------------------------------------------ #

    @abstractmethod
    async def _run(self) -> None: ...

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    async def start(self) -> None:
        """Start the background polling task. Idempotent."""
        if self._task and not self._task.done():
            return
        self._metrics.running = True
        self._metrics.healthy = True
        self._task = asyncio.create_task(self._run(), name=f"{self.name}-task")

    async def stop(self) -> None:
        """Cancel the polling task and await its clean exit."""
        self._metrics.running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(self._task), timeout=2.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
        self._task = None

    # ------------------------------------------------------------------ #
    # Health                                                               #
    # ------------------------------------------------------------------ #

    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    def get_metrics(self) -> ObserverMetrics:
        return self._metrics

    # ------------------------------------------------------------------ #
    # Page check — used by polling loops to exit on browser shutdown       #
    # ------------------------------------------------------------------ #

    def _page_is_closed(self) -> bool:
        """True if the page reference is gone or Playwright reports it closed."""
        return not page_is_usable(self._page)

    # ------------------------------------------------------------------ #
    # Metric helpers — called by subclasses each poll cycle               #
    # ------------------------------------------------------------------ #

    def _mark_poll(self) -> None:
        self._metrics.last_poll = datetime.now(timezone.utc)

    def _mark_success(self) -> None:
        self._metrics.last_success = datetime.now(timezone.utc)
        self._metrics.healthy = True
        self._metrics.error_count = max(0, self._metrics.error_count - 1)  # decay on success

    def _mark_error(self) -> None:
        self._metrics.error_count += 1
        # Unhealthy after 5 consecutive errors
        if self._metrics.error_count >= 5:
            self._metrics.healthy = False

