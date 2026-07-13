"""MeetingStateObserver — detects live meeting state via DOM banners and dialogs.

Distinct from JoinState (join flow) and SessionStatus (bot lifecycle).
This describes what is happening inside the meeting room itself.
Polls every 2 seconds (staggered between speaker @1s and participant @4s).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.meeting.intelligence.base import BaseObserver
from app.meeting.intelligence.context import MeetingContext
from app.meeting.intelligence.dom.meeting_dom import MeetingDOM
from app.meeting.intelligence.models import (
    EventType,
    MeetingEvent,
    MeetingState,
    get_event_category,
)
from app.meeting.utils.playwright_errors import is_playwright_fatal

_POLL_INTERVAL = 2.0  # seconds

_TERMINAL_STATES = frozenset({
    MeetingState.ENDED,
    MeetingState.BOT_REMOVED,
    MeetingState.HOST_ENDED,
})


class MeetingStateObserver(BaseObserver):
    """Observes meeting room state by scanning DOM in a background loop."""

    @property
    def name(self) -> str:
        return "meeting_state_observer"

    def __init__(self) -> None:
        super().__init__()
        self._ctx: MeetingContext | None = None
        self._dom = MeetingDOM()
        self._current_state: MeetingState = MeetingState.UNKNOWN
        self._state_history: list[tuple[datetime, MeetingState]] = []

    # ------------------------------------------------------------------ #
    # Public start / stop                                                  #
    # ------------------------------------------------------------------ #

    async def start(self, ctx: MeetingContext) -> None:
        self._ctx = ctx
        self._page = ctx.page
        await super().start()
        ctx.log.info(
            "meeting_state_observer.started",
            session_id=ctx.session_id,
        )

    async def stop(self) -> None:
        await super().stop()
        if self._ctx:
            self._ctx.log.info(
                "meeting_state_observer.stopped",
                session_id=self._ctx.session_id,
            )

    # ------------------------------------------------------------------ #
    # Data access                                                          #
    # ------------------------------------------------------------------ #

    def get_state(self) -> MeetingState:
        return self._current_state

    def get_state_history(self) -> list[tuple[datetime, MeetingState]]:
        return list(self._state_history)

    # ------------------------------------------------------------------ #
    # Polling loop                                                         #
    # ------------------------------------------------------------------ #

    async def _run(self) -> None:
        ctx = self._ctx
        while True:
            if self._page_is_closed():
                ctx.log.info("meeting_state_observer.page_closed — exiting", session_id=ctx.session_id)
                break

            await asyncio.sleep(_POLL_INTERVAL)
            self._mark_poll()
            try:
                await self._poll(ctx)
                self._mark_success()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                if is_playwright_fatal(exc):
                    ctx.log.info("meeting_state_observer.browser_gone — exiting", session_id=ctx.session_id)
                    break
                self._mark_error()
                ctx.log.warning(
                    "meeting_state_observer.poll_error",
                    session_id=ctx.session_id,
                    error=str(exc),
                    error_count=self._metrics.error_count,
                )

            # Stop polling once in a terminal state
            if self._current_state in _TERMINAL_STATES:
                ctx.log.info(
                    "meeting_state_observer.terminal_reached — stopping",
                    session_id=ctx.session_id,
                    state=self._current_state.value,
                )
                self._metrics.running = False
                break

    async def _poll(self, ctx: MeetingContext) -> None:
        detected = await self._dom.detect_state(ctx.page)
        if detected == self._current_state:
            return

        now = datetime.now(timezone.utc)
        old_state = self._current_state
        self._current_state = detected
        self._state_history.append((now, detected))

        ctx.log.info("meeting_state.detected", state=detected.value)

        # Choose the most semantically accurate event type
        if detected == MeetingState.IN_MEETING and old_state not in (
            MeetingState.IN_MEETING,
        ):
            event_type = EventType.MEETING_STARTED
            ctx.clock.start()
        elif detected in _TERMINAL_STATES:
            event_type = EventType.MEETING_ENDED
            ctx.clock.end()
        elif detected == MeetingState.NETWORK_LOST:
            event_type = EventType.NETWORK_LOST
        else:
            event_type = EventType.MEETING_STATE_CHANGED

        ctx.log.info(
            "meeting_state.changed",
            session_id=ctx.session_id,
            from_state=old_state.value,
            to_state=detected.value,
            event_type=event_type.value,
            elapsed_seconds=ctx.clock.meeting_elapsed,
        )

        await ctx.event_bus.emit(
            MeetingEvent(
                type=event_type,
                category=get_event_category(event_type),
                source=self.name,
                payload={
                    "previous_state": old_state.value,
                    "new_state": detected.value,
                    "elapsed_seconds": ctx.clock.meeting_elapsed,
                },
            )
        )
