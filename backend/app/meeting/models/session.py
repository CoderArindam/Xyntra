"""In-memory meeting session model.

M1.5 adds intelligence fields (participants_detailed, speaker_timeline, etc.)
while keeping the existing fields fully backward-compatible.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ------------------------------------------------------------------ #
# Status enumerations                                                  #
# ------------------------------------------------------------------ #

class SessionStatus(str, Enum):
    """Coarse-grained session lifecycle states."""

    STARTING = "starting"
    AUTHENTICATING = "authenticating"
    OPENING_MEET = "opening_meet"
    WAITING_LOBBY = "waiting_lobby"
    JOINING = "joining"
    IN_MEETING = "in_meeting"
    LEAVING = "leaving"
    CLEANING_UP = "cleaning_up"
    FINISHED = "finished"
    FAILED = "failed"


class JoinState(str, Enum):
    """Fine-grained join detection states returned by the meeting provider."""

    NOT_STARTED = "not_started"
    JOINING = "joining"
    WAITING_FOR_ADMISSION = "waiting_for_admission"
    IN_MEETING = "in_meeting"
    MEETING_NOT_FOUND = "meeting_not_found"
    MEETING_ENDED = "meeting_ended"
    PERMISSION_DENIED = "permission_denied"
    NETWORK_FAILURE = "network_failure"
    LOGIN_REQUIRED = "login_required"
    UNKNOWN_ERROR = "unknown_error"


# ------------------------------------------------------------------ #
# Active session statuses — used for concurrency limits               #
# ------------------------------------------------------------------ #

ACTIVE_STATUSES: frozenset[SessionStatus] = frozenset(
    {
        SessionStatus.STARTING,
        SessionStatus.AUTHENTICATING,
        SessionStatus.OPENING_MEET,
        SessionStatus.WAITING_LOBBY,
        SessionStatus.JOINING,
        SessionStatus.IN_MEETING,
        SessionStatus.CLEANING_UP,
    }
)

TERMINAL_STATUSES: frozenset[SessionStatus] = frozenset(
    {SessionStatus.FINISHED, SessionStatus.FAILED}
)


# ------------------------------------------------------------------ #
# Session model                                                        #
# ------------------------------------------------------------------ #

@dataclass
class MeetingSession:
    """Represents a single meeting bot session (in-memory only).

    Backward-compatible fields (M1):
        participants       — list[str] of present display names (kept for API compat)
        transcript_status  — placeholder for future transcription phase
        task_status        — placeholder for future task extraction phase

    Intelligence fields (M1.5):
        participants_detailed — full Participant objects (list[Any] to avoid
                                circular import; runtime type is list[Participant])
        participant_events    — raw MeetingEvent list for participant joins/leaves
        active_speaker        — current SpeakerSlot | None
        meeting_state         — string value of MeetingState enum
        meeting_started_at    — when IN_MEETING was first detected
        meeting_ended_at      — when a terminal state was detected
        peak_participants     — max simultaneous present participants
        meeting_duration      — seconds; None until meeting ends
        speaker_timeline      — completed SpeakerSlot list (append-only)
        intelligence_alive    — True when all observers are running
        observer_health       — per-observer metrics dict
    """

    meeting_url: str
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Lifecycle
    status: SessionStatus = SessionStatus.STARTING
    join_state: JoinState = JoinState.NOT_STARTED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    ended_at: datetime | None = None

    # Browser references (opaque identifiers, not Playwright objects)
    browser_pid: int | None = None
    page_id: str | None = None
    current_url: str | None = None

    # Legacy participants field — kept as list[str] for API backward compat
    participants: list[str] = field(default_factory=list)
    transcript_status: str = "none"
    task_status: str = "none"

    # Health
    browser_alive: bool = False
    page_alive: bool = False
    last_heartbeat: datetime | None = None

    # Diagnostics
    debug_dir: str | None = None
    error: str | None = None
    error_code: str | None = None

    # ── M1.5 Intelligence fields ──────────────────────────────────── #
    # list[Participant] — stored as Any to avoid intelligence→models import cycle
    participants_detailed: list[Any] = field(default_factory=list)
    participant_events: list[Any] = field(default_factory=list)   # list[MeetingEvent]
    active_speaker: Any | None = None                             # SpeakerSlot | None
    meeting_state: str = "unknown"                                # MeetingState.value
    meeting_started_at: datetime | None = None
    meeting_ended_at: datetime | None = None
    peak_participants: int = 0
    meeting_duration: float | None = None
    speaker_timeline: list[Any] = field(default_factory=list)    # list[SpeakerSlot]
    intelligence_alive: bool = False
    observer_health: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            # ── M1 core fields (unchanged) ──
            "session_id": self.session_id,
            "meeting_url": self.meeting_url,
            "status": self.status.value,
            "join_state": self.join_state.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "browser_pid": self.browser_pid,
            "page_id": self.page_id,
            "current_url": self.current_url,
            # Backward-compat: keep as list[str]
            "participants": self.participants,
            "transcript_status": self.transcript_status,
            "task_status": self.task_status,
            "browser_alive": self.browser_alive,
            "page_alive": self.page_alive,
            "last_heartbeat": (
                self.last_heartbeat.isoformat() if self.last_heartbeat else None
            ),
            "debug_dir": self.debug_dir,
            "error": self.error,
            "error_code": self.error_code,
            # ── M1.5 intelligence fields ──
            "participants_detailed": [
                p.to_dict() for p in self.participants_detailed
            ],
            "active_speaker": (
                self.active_speaker.to_dict() if self.active_speaker else None
            ),
            "meeting_state": self.meeting_state,
            "meeting_started_at": (
                self.meeting_started_at.isoformat() if self.meeting_started_at else None
            ),
            "meeting_ended_at": (
                self.meeting_ended_at.isoformat() if self.meeting_ended_at else None
            ),
            "peak_participants": self.peak_participants,
            "meeting_duration": self.meeting_duration,
            "speaker_timeline": [s.to_dict() for s in self.speaker_timeline],
            "intelligence_alive": self.intelligence_alive,
            "observer_health": self.observer_health,
        }
