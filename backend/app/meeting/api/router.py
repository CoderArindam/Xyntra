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

from typing import Optional
import asyncpg
from fastapi import APIRouter, HTTPException, Depends, status, Query

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
from app.auth.dependencies import require_meeting_initiation_access, get_current_user
from app.database.connection import get_db_connection
from app.schemas.envelope import DataEnvelope

log = get_logger("api")

from app.meeting.presence.router import router as presence_router

router = APIRouter(prefix="/meeting", tags=["meeting"])
router.include_router(presence_router, prefix="")

# Import the shared module-level singleton
from app.meeting.services.registry import meeting_service

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
# M1 endpoints                                                        #
# ------------------------------------------------------------------ #

@router.post("/join", response_model=JoinResponse)
async def join_meeting(
    request: JoinRequest,
    current_user: dict = Depends(require_meeting_initiation_access),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """Accept a meeting join request and immediately return a session ID.

    Requires Superadmin or Manager permission in the user's active organization.
    """
    org_id = current_user["organization_id"]
    user_id = current_user["id"]

    # Validate board_id if provided by caller
    if request.board_id is not None:
        board_org = await conn.fetchval(
            "SELECT organization_id FROM boards WHERE id = $1 AND deleted_at IS NULL",
            request.board_id
        )
        if board_org is None or board_org != org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Board does not belong to your organization"
            )

    try:
        # Create session row in DB using stored procedure fn_create_meeting_session
        session_row = await conn.fetchrow(
            """
            SELECT * FROM fn_create_meeting_session(
                $1::integer,
                $2::text,
                $3::integer,
                'manual'::meeting_source
            )
            """,
            org_id,
            request.meeting_url,
            user_id
        )

        db_session_id = str(session_row["id"]) if session_row else None

        session = await meeting_service.join_meeting(
            request.meeting_url,
            session_id=db_session_id,
            org_id=org_id,
            metadata={"org_id": org_id, "board_id": request.board_id}
        )
        session_id = session.session_id if session else db_session_id

        return JoinResponse(
            session_id=session_id,
            status=session.status.value if session else "starting",
            state=session.join_state.value if session else "joining",
            message=_STATE_MESSAGES.get(session.status.value if session else "starting", "Processing."),
        )
    except HTTPException:
        raise
    except RuntimeError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except Exception as exc:
        log.error("join_meeting endpoint error", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to initiate meeting join.")


@router.get("/sessions")
async def list_meeting_sessions(
    limit: Optional[int] = Query(None, ge=1, le=100, description="Optional maximum number of meeting sessions to return"),
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """Lists historical meeting sessions for the caller's organization using direct org_id column."""
    org_id = current_user["organization_id"]

    query = """
        SELECT * FROM v_meeting_sessions_canonical
        WHERE org_id = $1
        ORDER BY created_at DESC
    """
    args = [org_id]
    if limit is not None:
        query += " LIMIT $2"
        args.append(limit)

    rows = await conn.fetch(query, *args)

    return DataEnvelope(data=[dict(r) for r in rows])



@router.post("/leave/{session_id}", response_model=LeaveResponse)
async def leave_meeting(session_id: str):
    """Gracefully leave a meeting session.

    Clicks the Leave button if possible, otherwise closes the browser.
    """
    session = await meeting_service.leave_meeting(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    return LeaveResponse(
        session_id=session.session_id,
        status=session.status.value,
        message=_STATE_MESSAGES.get(session.status.value, "Session closed."),
    )


def _check_proposals_manifest(session_id: str) -> tuple[bool, int]:
    from pathlib import Path
    import json
    from app.meeting.config import meeting_config

    session_dir = Path(meeting_config.PROCESSING_OUTPUT_DIR) / session_id
    manifest_path = session_dir / "task_proposals_manifest.json"

    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            status = manifest.get("status")
            count = manifest.get("proposals_count", 0)
            if status == "completed":
                return True, int(count)
        except Exception:
            pass

    return False, 0


@router.get("/session/{session_id}", response_model=SessionResponse)
@router.get("/status/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get the current state and health of a meeting session.

    Returns all session fields including join_state, browser_alive,
    page_alive, last_heartbeat, current_url, M1.5 intelligence fields,
    and proposal status metadata (proposals_ready, proposals_count).
    Never throws noisy 404s for finished or inactive sessions.
    """
    session = meeting_service.get_session(session_id)
    ready, count = _check_proposals_manifest(session_id)

    if not session:
        from datetime import datetime, timezone
        return SessionResponse(
            session_id=session_id,
            meeting_url="",
            status="finished",
            join_state="meeting_ended",
            created_at=datetime.now(timezone.utc).isoformat(),
            proposals_ready=ready,
            proposals_count=count
        )

    session_data = session.to_dict()
    session_data["proposals_ready"] = ready
    session_data["proposals_count"] = count

    return SessionResponse(**session_data)


@router.delete("/session/{session_id}")
@router.delete("/sessions/{session_id}")
async def delete_meeting_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """Deletes a meeting session record and its linked task proposals staging records."""
    org_id = current_user["organization_id"]

    try:
        await conn.execute(
            "DELETE FROM task_proposals WHERE meeting_session_id::text = $1 AND org_id = $2",
            session_id, org_id
        )
        await conn.execute(
            "DELETE FROM meeting_sessions WHERE (id::text = $1 OR session_id = $1) AND org_id = $2",
            session_id, org_id
        )
    except Exception as exc:
        log.error("Failed to delete meeting session", session_id=session_id, error=str(exc))

    return DataEnvelope(data={"message": "Meeting session deleted successfully", "session_id": session_id})



# ------------------------------------------------------------------ #
# M1.5 endpoints                                                       #
# ------------------------------------------------------------------ #

@router.get("/session/{session_id}/participants", response_model=ParticipantListResponse)
async def get_participants(session_id: str):
    """Return the live participant list for a session.

    Includes all participants seen this session — both present and departed.
    `is_present` indicates current status.
    """
    session = meeting_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    participants = meeting_service.get_participants(session_id)
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
    session = meeting_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    events = meeting_service.get_timeline(session_id)

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
