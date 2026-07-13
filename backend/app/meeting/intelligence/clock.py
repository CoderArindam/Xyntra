"""MeetingClock — single source of truth for meeting time.

Future analytics and transcription alignment will reuse this object
instead of independently computing datetime differences.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class MeetingClock:
    """Tracks meeting start/end and exposes elapsed/duration helpers."""

    def __init__(self) -> None:
        self._start: datetime | None = None
        self._end: datetime | None = None

    def start(self) -> None:
        """Record meeting start. Idempotent — only first call has effect."""
        if self._start is None:
            self._start = datetime.now(timezone.utc)

    def end(self) -> None:
        """Record meeting end. Idempotent — only first call has effect."""
        if self._end is None:
            self._end = datetime.now(timezone.utc)

    @property
    def meeting_start(self) -> datetime | None:
        return self._start

    @property
    def meeting_elapsed(self) -> float:
        """Seconds elapsed since meeting started. 0 if not yet started."""
        if self._start is None:
            return 0.0
        anchor = self._end or datetime.now(timezone.utc)
        return round((anchor - self._start).total_seconds(), 3)

    @property
    def meeting_duration(self) -> float | None:
        """Total duration in seconds. None if meeting has not ended."""
        if self._start is None or self._end is None:
            return None
        return round((self._end - self._start).total_seconds(), 3)

    def to_dict(self) -> dict[str, Any]:
        return {
            "meeting_start": self._start.isoformat() if self._start else None,
            "meeting_elapsed": self.meeting_elapsed,
            "meeting_duration": self.meeting_duration,
        }
