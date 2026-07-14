"""ParticipantTracker — observes the Meet participant panel to track joins and leaves.

No audio, no recording, no transcription.
Polls the participant panel DOM every 4 seconds (staggered from other observers).
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from app.meeting.intelligence.base import BaseObserver
from app.meeting.intelligence.context import MeetingContext
from app.meeting.intelligence.dom.participant_dom import ParticipantDOM
from app.meeting.intelligence.models import (
    EventType,
    MeetingEvent,
    Participant,
    get_event_category,
)
from app.meeting.utils.playwright_errors import is_playwright_fatal

_POLL_INTERVAL = 4.0   # seconds — slowest observer; participant changes are infrequent


def _normalize(name: str) -> str:
    return name.lower().strip()


class ParticipantTracker(BaseObserver):
    """Tracks who is in the meeting by polling the participant panel.

    State:
        _participants — keyed by normalized_name; all participants seen this session.
        join_counter  — monotonically increasing join order.
    """

    @property
    def name(self) -> str:
        return "participant_tracker"

    def __init__(self) -> None:
        super().__init__()
        self._ctx: MeetingContext | None = None
        self._dom = ParticipantDOM()
        self._participants: dict[str, Participant] = {}
        self._join_counter: int = 0

    # ------------------------------------------------------------------ #
    # Public start / stop                                                  #
    # ------------------------------------------------------------------ #

    async def start(self, ctx: MeetingContext) -> None:
        self._ctx = ctx
        self._page = ctx.page
        await super().start()
        ctx.log.info(
            "participant_tracker.started",
            session_id=ctx.session_id,
        )

    async def stop(self) -> None:
        await super().stop()
        if self._ctx:
            self._ctx.log.info(
                "participant_tracker.stopped",
                session_id=self._ctx.session_id,
            )

    # ------------------------------------------------------------------ #
    # Data access                                                          #
    # ------------------------------------------------------------------ #

    def get_participants(self) -> list[Participant]:
        """All participants seen this session (present and departed)."""
        return list(self._participants.values())

    def get_present_participants(self) -> list[Participant]:
        return [p for p in self._participants.values() if p.is_present]

    # ------------------------------------------------------------------ #
    # Polling loop                                                         #
    # ------------------------------------------------------------------ #

    async def _run(self) -> None:
        ctx = self._ctx

        while True:
            if self._page_is_closed():
                ctx.log.info("participant_tracker.page_closed — exiting", session_id=ctx.session_id)
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
                    ctx.log.info("participant_tracker.browser_gone — exiting", session_id=ctx.session_id)
                    break
                self._mark_error()
                ctx.log.warning(
                    "participant_tracker.poll_error",
                    session_id=ctx.session_id,
                    error=str(exc),
                    error_count=self._metrics.error_count,
                )

    async def _poll(self, ctx: MeetingContext) -> None:
        now = datetime.now(timezone.utc)
        
        raw_list = await self._dom.get_raw_participants(ctx.page)
                
        seen_keys: set[str] = set()

        # Save previous state for logging
        previous_participants = [p.display_name for p in self.get_present_participants()]
        joined_names = []
        left_names = []
        events_emitted = []

        for entry in raw_list:
            raw_name: str = entry["name"]
            is_host: bool = entry.get("is_host", False)
            is_self: bool = entry.get("is_self", False)
            norm: str = _normalize(raw_name)
            if not norm:
                continue
            seen_keys.add(norm)

            if norm in self._participants:
                p = self._participants[norm]
                p.last_seen = now
                if not p.is_present:
                    # Rejoined
                    p.is_present = True
                    p.join_time = now
                    p.leave_time = None
                    await self._emit_event(ctx, EventType.PARTICIPANT_JOINED, p)
                    joined_names.append(p.display_name)
                    events_emitted.append(EventType.PARTICIPANT_JOINED.value)
            else:
                # First sighting
                self._join_counter += 1
                is_bot = (
                    is_self or _normalize(raw_name) == _normalize(ctx.bot_name)
                )
                p = Participant(
                    participant_id=str(uuid.uuid4()),
                    display_name=raw_name,
                    normalized_name=norm,
                    join_order=self._join_counter,
                    is_bot=is_bot,
                    is_present=True,
                    join_time=now,
                    first_seen=now,
                    last_seen=now,
                    avatar_url=entry.get("avatar_url"),
                )
                self._participants[norm] = p
                await self._emit_event(ctx, EventType.PARTICIPANT_JOINED, p)
                joined_names.append(p.display_name)
                events_emitted.append(EventType.PARTICIPANT_JOINED.value)

                ctx.log.info(
                    "participant.joined",
                    session_id=ctx.session_id,
                    display_name=p.display_name,
                    is_bot=p.is_bot,
                    join_order=p.join_order,
                    participant_count=len(self.get_present_participants()),
                    meeting_state=ctx.clock.meeting_elapsed,
                )

                if is_host:
                    await self._emit_event(ctx, EventType.HOST_JOINED, p)
                    events_emitted.append(EventType.HOST_JOINED.value)
                    ctx.log.info(
                        "participant.host_joined",
                        session_id=ctx.session_id,
                        display_name=p.display_name,
                    )

        # Detect departures
        for norm, p in self._participants.items():
            if p.is_present and norm not in seen_keys:
                p.is_present = False
                p.leave_time = now
                await self._emit_event(ctx, EventType.PARTICIPANT_LEFT, p)
                left_names.append(p.display_name)
                events_emitted.append(EventType.PARTICIPANT_LEFT.value)
                ctx.log.info(
                    "participant.left",
                    session_id=ctx.session_id,
                    display_name=p.display_name,
                    participant_count=len(self.get_present_participants()),
                )

        pass

    async def _emit_event(
        self, ctx: MeetingContext, event_type: EventType, participant: Participant
    ) -> None:
        await ctx.event_bus.emit(
            MeetingEvent(
                type=event_type,
                category=get_event_category(event_type),
                source=self.name,
                payload={
                    "participant": participant.to_dict(),
                    "participant_count": len(self.get_present_participants()),
                    "elapsed_seconds": ctx.clock.meeting_elapsed,
                },
            )
        )
