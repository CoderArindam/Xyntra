"""Meeting API router — fully isolated from existing KAIO routes.

Endpoints (M1):
    POST /meeting/join                  — fire-and-forget async join
    POST /meeting/leave/{session_id}    — graceful leave
    GET  /meeting/session/{session_id}  — session status + health + intelligence

Endpoints (M1.5):
    GET  /meeting/session/{session_id}/participants  — live participant list
    GET  /meeting/session/{session_id}/timeline      — chronological event history

All responses are machine-friendly with explicit state and message fields.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.meeting.logger import get_logger
from app.meeting.schemas.meeting import (
    JoinRequest,
    JoinResponse,
    LeaveResponse,
    ParticipantListResponse,
    SessionResponse,
    TimelineEvent,
    TimelineResponse,
)
from app.meeting.services.meeting_service import MeetingService

log = get_logger("api")

router = APIRouter(prefix="/meeting", tags=["meeting"])

# Module-level singleton — stateless at import; no side effects until a
# request is received.
_service = MeetingService()

_STATE_MESSAGES: dict[str, str] = {
    "starting":       "Bot is initialising.",
    "authenticating": "Bot is verifying Google credentials.",
    "opening_meet":   "Bot is navigating to the meeting URL.",
    "joining":        "Bot is attempting to join the meeting.",
    "waiting_lobby":  "Bot is waiting in the lobby for admission.",
    "in_meeting":     "Bot has joined the meeting successfully.",
    "leaving":        "Bot is leaving the meeting.",
    "cleaning_up":    "Bot is cleaning up session resources.",
    "finished":       "Meeting session has ended cleanly.",
    "failed":         "Meeting session failed. Check error_code for details.",
}


# ------------------------------------------------------------------ #
# M1 endpoints (unchanged)                                             #
# ------------------------------------------------------------------ #

@router.post("/join", response_model=JoinResponse)
async def join_meeting(request: JoinRequest):
    """Accept a meeting join request and immediately return a session ID.

    The bot join runs asynchronously. Poll GET /meeting/session/{id} for
    real-time status updates.
    """
    try:
        session = await _service.join_meeting(request.meeting_url)
        return JoinResponse(
            session_id=session.session_id,
            status=session.status.value,
            state=session.join_state.value,
            message=_STATE_MESSAGES.get(session.status.value, "Processing."),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except Exception as exc:
        log.error("join_meeting endpoint error", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to initiate meeting join.")


@router.post("/leave/{session_id}", response_model=LeaveResponse)
async def leave_meeting(session_id: str):
    """Gracefully leave a meeting session.

    Clicks the Leave button if possible, otherwise closes the browser.
    """
    session = await _service.leave_meeting(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    return LeaveResponse(
        session_id=session.session_id,
        status=session.status.value,
        message=_STATE_MESSAGES.get(session.status.value, "Session closed."),
    )


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get the current state and health of a meeting session.

    Returns all session fields including join_state, browser_alive,
    page_alive, last_heartbeat, current_url, and all M1.5 intelligence fields.
    """
    session = _service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return SessionResponse(**session.to_dict())


# ------------------------------------------------------------------ #
# M1.5 endpoints                                                       #
# ------------------------------------------------------------------ #

@router.get("/session/{session_id}/participants", response_model=ParticipantListResponse)
async def get_participants(session_id: str):
    """Return the live participant list for a session.

    Includes all participants seen this session — both present and departed.
    `is_present` indicates current status.
    """
    session = _service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    participants = _service.get_participants(session_id)
    present_count = sum(1 for p in participants if p.is_present)

    return ParticipantListResponse(
        session_id=session_id,
        count=len(participants),
        present_count=present_count,
        participants=[p.to_dict() for p in participants],
    )


@router.get("/session/{session_id}/timeline", response_model=TimelineResponse)
async def get_timeline(session_id: str):
    """Return all intelligence events in chronological order.

    Event categories: participant | speaker | meeting | system | network

    This timeline is the single source of truth for:
    - When each participant joined / left
    - When each speaker spoke (and for how long)
    - Meeting state transitions
    - Observer lifecycle events

    Future transcription alignment will use speaker slot timestamps from this timeline.
    """
    session = _service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    events = _service.get_timeline(session_id)

    return TimelineResponse(
        session_id=session_id,
        event_count=len(events),
        events=[
            TimelineEvent(
                event_id=e.event_id,
                timestamp=e.timestamp.isoformat(),
                type=e.type.value,
                category=e.category.value,
                source=e.source,
                payload=e.payload,
            )
            for e in events
        ],
    )
