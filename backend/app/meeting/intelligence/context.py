"""MeetingContext — shared context passed to every intelligence component.

Eliminates passing page, session_id, logger, and config as separate arguments.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app.meeting.intelligence.clock import MeetingClock
from app.meeting.intelligence.event_bus import EventBus
from app.meeting.logger import MeetingLogger, get_logger

if TYPE_CHECKING:
    from app.meeting.config import MeetingSettings


@dataclass
class MeetingContext:
    """Shared context for all intelligence components.

    Created once per session by MeetingService and passed to every observer
    and DOM accessor. Observers store a reference; never copy individual fields.
    """

    session_id: str
    page: Any                           # Playwright Page — opaque to intelligence layer
    config: "MeetingSettings"
    event_bus: EventBus
    clock: MeetingClock
    bot_name: str
    log: MeetingLogger = field(init=False)

    def __post_init__(self) -> None:
        self.log = get_logger(f"intelligence.{self.session_id[:8]}")
