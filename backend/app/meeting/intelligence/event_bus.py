"""In-memory EventBus for the Meeting Intelligence Layer.

Observers emit events. MeetingService subscribes to update session state.
Observers never modify session state directly — keeping them loosely coupled.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Callable, Coroutine

from app.meeting.intelligence.models import EventCategory, EventType, MeetingEvent
from app.meeting.logger import get_logger

log = get_logger("intelligence.event_bus")

# Handler signature: async def handler(event: MeetingEvent) -> None
Handler = Callable[[MeetingEvent], Coroutine]


class EventBus:
    """Lightweight async pub/sub for meeting intelligence events.

    - Subscribe with event_type=None to receive every event.
    - History is append-only and chronologically ordered.
    - Handlers that raise are logged and silently skipped.
    """

    def __init__(self) -> None:
        self._handlers: dict[EventType | None, list[Handler]] = defaultdict(list)
        self._history: list[MeetingEvent] = []  # append-only; never removed

    # ------------------------------------------------------------------ #
    # Subscription                                                         #
    # ------------------------------------------------------------------ #

    def subscribe(self, event_type: EventType | None, handler: Handler) -> None:
        """Register a handler. Pass event_type=None to catch all events."""
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType | None, handler: Handler) -> None:
        try:
            self._handlers[event_type].remove(handler)
        except ValueError:
            pass

    # ------------------------------------------------------------------ #
    # Emit                                                                 #
    # ------------------------------------------------------------------ #

    async def emit(self, event: MeetingEvent) -> None:
        """Append to history and call matching handlers."""
        log.info("event.emitted", event=event.type.value)
        self._history.append(event)

        # Collect type-specific + wildcard handlers (avoid duplicates)
        handlers = list(self._handlers.get(event.type, []))
        handlers += [h for h in self._handlers.get(None, []) if h not in handlers]

        for handler in handlers:
            try:
                await handler(event)
            except Exception as exc:
                log.warning(
                    "Event handler raised",
                    event_type=event.type.value,
                    source=event.source,
                    error=str(exc),
                )

    # ------------------------------------------------------------------ #
    # History queries                                                      #
    # ------------------------------------------------------------------ #

    def get_history(self) -> list[MeetingEvent]:
        """Return a snapshot of all events in chronological order."""
        return list(self._history)

    def get_history_by_category(self, category: EventCategory) -> list[MeetingEvent]:
        return [e for e in self._history if e.category == category]

    def get_history_by_type(self, event_type: EventType) -> list[MeetingEvent]:
        return [e for e in self._history if e.type == event_type]
