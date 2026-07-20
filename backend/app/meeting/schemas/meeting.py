"""Pydantic schemas for meeting API endpoints.

M1.5 adds:
  - ParticipantSchema, SpeakerSlotSchema
  - ParticipantListResponse
  - TimelineEvent, TimelineResponse
  - SessionResponse extended with intelligence fields
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


# ------------------------------------------------------------------ #
# Request                                                              #
# ------------------------------------------------------------------ #

class JoinRequest(BaseModel):
    meeting_url: str
    board_id: int | None = None



# ------------------------------------------------------------------ #
# Responses — M1 (unchanged)                                          #
# ------------------------------------------------------------------ #

class JoinResponse(BaseModel):
    session_id: str
    status: str
    state: str
    message: str


class LeaveResponse(BaseModel):
    session_id: str
    status: str
    message: str


# ------------------------------------------------------------------ #
# Intelligence schemas — M1.5                                         #
# ------------------------------------------------------------------ #

class ParticipantSchema(BaseModel):
    participant_id: str
    display_name: str
    normalized_name: str
    join_order: int
    is_bot: bool
    is_present: bool
    join_time: str
    leave_time: str | None = None
    first_seen: str
    last_seen: str
    avatar_url: str | None = None


class SpeakerSlotSchema(BaseModel):
    slot_id: str
    participant_id: str | None = None
    display_name: str
    start_time: str
    end_time: str | None = None
    duration_seconds: float | None = None


class ObserverHealthSchema(BaseModel):
    running: bool
    healthy: bool
    last_poll: str | None = None
    last_success: str | None = None
    error_count: int
    restart_count: int


# ------------------------------------------------------------------ #
# Session response — extended                                          #
# ------------------------------------------------------------------ #

class SessionResponse(BaseModel):
    # ── M1 core fields ──
    session_id: str
    meeting_url: str
    status: str
    join_state: str
    created_at: str
    started_at: str | None = None
    ended_at: str | None = None
    browser_pid: int | None = None
    page_id: str | None = None
    current_url: str | None = None
    participants: list[str] = []        # backward-compat: display names of present participants
    transcript_status: str = "none"
    task_status: str = "none"
    browser_alive: bool = False
    page_alive: bool = False
    last_heartbeat: str | None = None
    debug_dir: str | None = None
    error: str | None = None
    error_code: str | None = None
    # ── M1.5 intelligence fields ──
    participants_detailed: list[dict[str, Any]] = []
    active_speaker: dict[str, Any] | None = None
    meeting_state: str = "unknown"
    meeting_started_at: str | None = None
    meeting_ended_at: str | None = None
    peak_participants: int = 0
    meeting_duration: float | None = None
    speaker_timeline: list[dict[str, Any]] = []
    intelligence_alive: bool = False
    observer_health: dict[str, Any] = {}
    # ── M3 proposals fields ──
    proposals_ready: bool = False
    proposals_count: int = 0



# ------------------------------------------------------------------ #
# GET /session/{id}/participants                                        #
# ------------------------------------------------------------------ #

class ParticipantListResponse(BaseModel):
    session_id: str
    count: int
    present_count: int
    participants: list[dict[str, Any]]


# ------------------------------------------------------------------ #
# GET /session/{id}/timeline                                           #
# ------------------------------------------------------------------ #

class TimelineEvent(BaseModel):
    event_id: str
    timestamp: str
    type: str
    category: str
    source: str
    payload: dict[str, Any]


class TimelineResponse(BaseModel):
    session_id: str
    event_count: int
    events: list[TimelineEvent]
