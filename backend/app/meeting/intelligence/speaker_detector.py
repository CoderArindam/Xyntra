"""SpeakerDetector — detects who is speaking via Meet UI observation.

No audio capture. No recording. DOM only.
Polls every 1 second (fastest observer — speaker changes frequently).
Maintains an append-only speaker timeline for future transcription alignment.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.meeting.intelligence.base import BaseObserver
from app.meeting.intelligence.context import MeetingContext
from app.meeting.intelligence.dom.speaker_dom import SpeakerDOM
from app.meeting.intelligence.models import (
    EventType,
    MeetingEvent,
    SpeakerSlot,
    get_event_category,
)
from app.meeting.utils.playwright_errors import is_playwright_fatal

_POLL_INTERVAL = 1.0  # seconds — speaker changes are fast


class SpeakerDetector(BaseObserver):
    """Maintains active speaker and a closed, append-only speaker timeline.

    Timeline rules:
    - Slots are never mutated after being appended.
    - `close()` returns a new completed slot rather than editing in place.
    - Later transcription alignment consumes the timeline as-is.
    """

    @property
    def name(self) -> str:
        return "speaker_detector"

    def __init__(self) -> None:
        super().__init__()
        self._ctx: MeetingContext | None = None
        self._dom = SpeakerDOM()
        self._current_slot: SpeakerSlot | None = None
        self._timeline: list[SpeakerSlot] = []  # append-only

    # ------------------------------------------------------------------ #
    # Public start / stop                                                  #
    # ------------------------------------------------------------------ #

    async def start(self, ctx: MeetingContext) -> None:
        self._ctx = ctx
        self._page = ctx.page
        await super().start()
        ctx.log.info("speaker_detector.started", session_id=ctx.session_id)

    async def stop(self) -> None:
        """Close the current speaking slot before stopping."""
        if self._current_slot:
            closed = self._current_slot.close(datetime.now(timezone.utc))
            self._timeline.append(closed)
            self._current_slot = None
        await super().stop()
        if self._ctx:
            self._ctx.log.info(
                "speaker_detector.stopped",
                session_id=self._ctx.session_id,
            )

    # ------------------------------------------------------------------ #
    # Data access                                                          #
    # ------------------------------------------------------------------ #

    def get_active_speaker(self) -> SpeakerSlot | None:
        """Currently speaking slot (open — no end_time yet)."""
        return self._current_slot

    def get_speaker_timeline(self) -> list[SpeakerSlot]:
        """All completed (closed) speaking slots in chronological order."""
        return list(self._timeline)

    # ------------------------------------------------------------------ #
    # Polling loop                                                         #
    # ------------------------------------------------------------------ #

    async def _run(self) -> None:
        ctx = self._ctx
        while True:
            if self._page_is_closed():
                ctx.log.info("speaker_detector.page_closed — exiting", session_id=ctx.session_id)
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
                    ctx.log.info("speaker_detector.browser_gone — exiting", session_id=ctx.session_id)
                    break
                self._mark_error()
                ctx.log.warning(
                    "speaker_detector.poll_error",
                    session_id=ctx.session_id,
                    error=str(exc),
                    error_count=self._metrics.error_count,
                )

    async def _poll(self, ctx: MeetingContext) -> None:
        speaker_name = await self._dom.get_active_speaker_name(ctx.page)
        now = datetime.now(timezone.utc)

        current_name = self._current_slot.display_name if self._current_slot else None
        if speaker_name == current_name:
            return  # No change; skip event

        # Close previous slot
        completed: SpeakerSlot | None = None
        if self._current_slot:
            completed = self._current_slot.close(now)
            self._timeline.append(completed)  # append-only — never mutate
            self._current_slot = None

        # Open new slot
        if speaker_name:
            self._current_slot = SpeakerSlot(display_name=speaker_name, start_time=now)
            ctx.log.info(
                "speaker.changed",
                session_id=ctx.session_id,
                speaker=speaker_name,
                elapsed_seconds=ctx.clock.meeting_elapsed,
            )

        await ctx.event_bus.emit(
            MeetingEvent(
                type=EventType.SPEAKER_CHANGED,
                category=get_event_category(EventType.SPEAKER_CHANGED),
                source=self.name,
                payload={
                    "current_speaker": self._current_slot.to_dict() if self._current_slot else None,
                    "completed_slot": completed.to_dict() if completed else None,
                    "elapsed_seconds": ctx.clock.meeting_elapsed,
                },
            )
        )
