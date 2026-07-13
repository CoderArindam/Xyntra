"""Data models for the Meeting Intelligence Layer.

Pure Python dataclasses. No Playwright, FastAPI, or database references.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ------------------------------------------------------------------ #
# Enumerations                                                         #
# ------------------------------------------------------------------ #

class MeetingState(str, Enum):
    """Live state of the meeting — independent of JoinState and SessionStatus."""

    UNKNOWN = "unknown"
    LOBBY = "lobby"
    CONNECTING = "connecting"
    IN_MEETING = "in_meeting"
    RECONNECTING = "reconnecting"
    NETWORK_LOST = "network_lost"
    ENDED = "ended"
    BOT_REMOVED = "bot_removed"
    HOST_ENDED = "host_ended"
    WAITING_FOR_HOST = "waiting_for_host"


class EventType(str, Enum):
    PARTICIPANT_JOINED = "participant_joined"
    PARTICIPANT_LEFT = "participant_left"
    PARTICIPANT_UPDATED = "participant_updated"
    SPEAKER_CHANGED = "speaker_changed"
    MEETING_STATE_CHANGED = "meeting_state_changed"
    MEETING_STARTED = "meeting_started"
    MEETING_ENDED = "meeting_ended"
    HOST_JOINED = "host_joined"
    NETWORK_LOST = "network_lost"
    OBSERVER_RESTARTED = "observer_restarted"
    OBSERVER_FAILED = "observer_failed"


class EventCategory(str, Enum):
    PARTICIPANT = "participant"
    SPEAKER = "speaker"
    MEETING = "meeting"
    SYSTEM = "system"
    NETWORK = "network"


_EVENT_CATEGORIES: dict[EventType, EventCategory] = {
    EventType.PARTICIPANT_JOINED: EventCategory.PARTICIPANT,
    EventType.PARTICIPANT_LEFT: EventCategory.PARTICIPANT,
    EventType.PARTICIPANT_UPDATED: EventCategory.PARTICIPANT,
    EventType.SPEAKER_CHANGED: EventCategory.SPEAKER,
    EventType.MEETING_STATE_CHANGED: EventCategory.MEETING,
    EventType.MEETING_STARTED: EventCategory.MEETING,
    EventType.MEETING_ENDED: EventCategory.MEETING,
    EventType.HOST_JOINED: EventCategory.MEETING,
    EventType.NETWORK_LOST: EventCategory.NETWORK,
    EventType.OBSERVER_RESTARTED: EventCategory.SYSTEM,
    EventType.OBSERVER_FAILED: EventCategory.SYSTEM,
}


def get_event_category(event_type: EventType) -> EventCategory:
    return _EVENT_CATEGORIES.get(event_type, EventCategory.SYSTEM)


# ------------------------------------------------------------------ #
# Participant                                                          #
# ------------------------------------------------------------------ #

@dataclass
class Participant:
    """Represents a single meeting participant.

    participant_id — stable synthetic UUID, not Meet's internal ID.
    normalized_name — lowercase-stripped name; survives display name changes.
    join_order — 1-indexed order of first appearance.
    """

    participant_id: str
    display_name: str
    normalized_name: str
    join_order: int
    is_bot: bool
    is_present: bool = True
    join_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    leave_time: datetime | None = None
    first_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    avatar_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "participant_id": self.participant_id,
            "display_name": self.display_name,
            "normalized_name": self.normalized_name,
            "join_order": self.join_order,
            "is_bot": self.is_bot,
            "is_present": self.is_present,
            "join_time": self.join_time.isoformat(),
            "leave_time": self.leave_time.isoformat() if self.leave_time else None,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "avatar_url": self.avatar_url,
        }


# ------------------------------------------------------------------ #
# Speaker                                                              #
# ------------------------------------------------------------------ #

@dataclass
class SpeakerSlot:
    """One continuous speaking interval.

    Append-only: once added to the timeline, a slot is never mutated.
    `close()` returns a new completed slot rather than mutating self.
    """

    slot_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    participant_id: str | None = None
    display_name: str = ""
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: datetime | None = None         # None = currently speaking
    duration_seconds: float | None = None    # computed on close

    def close(self, end_time: datetime) -> "SpeakerSlot":
        """Return a new completed SpeakerSlot. Self is unchanged."""
        return SpeakerSlot(
            slot_id=self.slot_id,
            participant_id=self.participant_id,
            display_name=self.display_name,
            start_time=self.start_time,
            end_time=end_time,
            duration_seconds=round((end_time - self.start_time).total_seconds(), 3),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "participant_id": self.participant_id,
            "display_name": self.display_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
        }


# ------------------------------------------------------------------ #
# Events                                                               #
# ------------------------------------------------------------------ #

@dataclass
class MeetingEvent:
    """An immutable intelligence event.

    Every event has a stable event_id for replay and debugging.
    Payload is open-ended to support future consumers (transcription, tasks).
    """

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    type: EventType = EventType.MEETING_STARTED
    category: EventCategory = EventCategory.MEETING
    source: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "type": self.type.value,
            "category": self.category.value,
            "source": self.source,
            "payload": self.payload,
        }


# ------------------------------------------------------------------ #
# Observer metrics                                                     #
# ------------------------------------------------------------------ #

@dataclass
class ObserverMetrics:
    """Live health metrics for a single observer. Updated in-place."""

    running: bool = False
    healthy: bool = False
    last_poll: datetime | None = None
    last_success: datetime | None = None
    error_count: int = 0
    restart_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "running": self.running,
            "healthy": self.healthy,
            "last_poll": self.last_poll.isoformat() if self.last_poll else None,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "error_count": self.error_count,
            "restart_count": self.restart_count,
        }
