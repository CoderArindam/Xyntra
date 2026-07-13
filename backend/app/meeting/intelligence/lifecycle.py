"""MeetingLifecycle — aggregated meeting analytics.

Passive aggregator: no background tasks, no polling.
Updated exclusively by MeetingService via event subscriptions.
Later phases will extend this for analytics and reporting.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class MeetingLifecycle:
    """Accumulates meeting-level analytics for a single session."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self._meeting_start: datetime | None = None
        self._meeting_end: datetime | None = None
        self._peak_participants: int = 0
        self._current_participants: int = 0
        self._host_detected: str | None = None
        self._waiting_time_seconds: float | None = None
        self._join_duration_seconds: float | None = None

    # ------------------------------------------------------------------ #
    # Mutators — called by MeetingService event handler                   #
    # ------------------------------------------------------------------ #

    def record_start(self, time: datetime) -> None:
        if self._meeting_start is None:
            self._meeting_start = time

    def record_end(self, time: datetime) -> None:
        if self._meeting_end is None:
            self._meeting_end = time

    def record_host(self, display_name: str) -> None:
        if self._host_detected is None:
            self._host_detected = display_name

    def record_waiting_time(self, seconds: float) -> None:
        self._waiting_time_seconds = seconds

    def record_join_duration(self, seconds: float) -> None:
        self._join_duration_seconds = seconds

    def update_participant_count(self, count: int) -> None:
        self._current_participants = count
        if count > self._peak_participants:
            self._peak_participants = count

    # ------------------------------------------------------------------ #
    # Computed properties                                                  #
    # ------------------------------------------------------------------ #

    @property
    def peak_participants(self) -> int:
        return self._peak_participants

    @property
    def duration_seconds(self) -> float | None:
        if self._meeting_start is None:
            return None
        anchor = self._meeting_end or datetime.now(timezone.utc)
        return round((anchor - self._meeting_start).total_seconds(), 3)

    def to_dict(self) -> dict[str, Any]:
        return {
            "meeting_start": self._meeting_start.isoformat() if self._meeting_start else None,
            "meeting_end": self._meeting_end.isoformat() if self._meeting_end else None,
            "duration_seconds": self.duration_seconds,
            "peak_participants": self._peak_participants,
            "current_participants": self._current_participants,
            "host_detected": self._host_detected,
            "waiting_time_seconds": self._waiting_time_seconds,
            "join_duration_seconds": self._join_duration_seconds,
        }
