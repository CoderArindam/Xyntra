import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.auth.dependencies import get_current_user
from app.database.connection import get_db_connection
from app.services.notification_service import notify_timesheet_approved, notify_timesheet_rejected
from app.schemas.timesheet_approvals import (
    ApprovalQueueItemResponse,
    ApprovalQueueSummaryResponse,
    ApproveTimesheetRequest,
    RejectTimesheetRequest,
)
from app.schemas.timesheets import TimesheetResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/timesheets", tags=["Timesheet Approvals"])


def _parse_uuid(val: str | UUID | int | None) -> UUID | None:
    if val is None:
        return None
    if isinstance(val, UUID):
        return val
    s_val = str(val).strip()
    if s_val.isdigit():
        return UUID(f"00000000-0000-0000-0000-{int(s_val):012d}")
    try:
        return UUID(s_val)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: {val}",
        )


def _check_superadmin_or_manager(current_user: dict):
    role = str(current_user.get("role") or "").lower()
    if role not in ("superadmin", "super_admin", "manager"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Manager or Superadmin role required",
        )


from app.routers.timesheet_errors import handle_timesheet_db_error


def _handle_db_exception(e: Exception):
    handle_timesheet_db_error(e)


@router.get("/approvals/queue", response_model=List[ApprovalQueueItemResponse])
async def get_approval_queue(
    status_filter: str = Query("submitted", alias="status"),
    board_id: Optional[UUID] = Query(None),
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    """Retrieve timesheet approval queue for manager/superadmin."""
    _check_superadmin_or_manager(current_user)
    user_id = _parse_uuid(current_user.get("id"))
    org_id = _parse_uuid(current_user.get("organization_id"))

    base_where = "WHERE org_id = $1 AND (approver_id = $2 OR approver_id IS NULL) AND user_id != $2"
    params = [org_id, user_id]

    if status_filter and status_filter.lower() != "all":
        params.append(status_filter.lower())
        base_where += f" AND status = ${len(params)}"

    if board_id:
        params.append(board_id)
        base_where += f" AND id IN (SELECT DISTINCT timesheet_id FROM v_timesheet_entries_canonical WHERE board_id = ${len(params)})"

    query = f"SELECT * FROM v_timesheets_canonical {base_where} ORDER BY submitted_at DESC, week_start_date DESC"
    rows = await conn.fetch(query, *params)

    now = datetime.now(timezone.utc)
    result = []
    for row in rows:
        row_dict = dict(row)
        submitted_at = row_dict.get("submitted_at")
        if submitted_at:
            if submitted_at.tzinfo is None:
                submitted_at = submitted_at.replace(tzinfo=timezone.utc)
            delta = now - submitted_at
            days_since_submitted = max(0, delta.days)
            is_overdue = delta.total_seconds() > (48 * 3600)
        else:
            days_since_submitted = 0
            is_overdue = False

        board_rows = await conn.fetch(
            "SELECT DISTINCT board_name FROM v_timesheet_entries_canonical WHERE timesheet_id = $1 AND board_name IS NOT NULL",
            row_dict["id"],
        )
        boards_involved = [b["board_name"] for b in board_rows if b["board_name"]]

        row_dict["days_since_submitted"] = days_since_submitted
        row_dict["is_overdue"] = is_overdue
        row_dict["boards_involved"] = boards_involved

        result.append(ApprovalQueueItemResponse.model_validate(row_dict))

    return result


@router.get("/approvals/queue/summary", response_model=ApprovalQueueSummaryResponse)
async def get_approval_queue_summary(
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    """Retrieve summary metrics for manager approval queue."""
    _check_superadmin_or_manager(current_user)
    user_id = _parse_uuid(current_user.get("id"))
    org_id = _parse_uuid(current_user.get("organization_id"))

    where_clause = "WHERE org_id = $1 AND (approver_id = $2 OR approver_id IS NULL) AND user_id != $2"
    params = [org_id, user_id]

    q1 = f"SELECT COUNT(*)::INTEGER FROM v_timesheets_canonical {where_clause} AND status = 'submitted'"
    pending_count = await conn.fetchval(q1, *params) or 0

    q2 = f"SELECT COUNT(*)::INTEGER FROM v_timesheets_canonical {where_clause} AND status = 'approved' AND reviewed_at >= date_trunc('week', NOW())"
    approved_this_week = await conn.fetchval(q2, *params) or 0

    q3 = f"SELECT COUNT(*)::INTEGER FROM v_timesheets_canonical {where_clause} AND status = 'rejected' AND reviewed_at >= date_trunc('week', NOW())"
    rejected_this_week = await conn.fetchval(q3, *params) or 0

    q4 = f"SELECT AVG(total_hours) FROM v_timesheets_canonical {where_clause} AND status = 'approved' AND reviewed_at >= (NOW() - INTERVAL '30 days')"
    raw_avg = await conn.fetchval(q4, *params)
    avg_hours_approved = round(float(raw_avg), 2) if raw_avg is not None else 0.0

    q5 = f"SELECT MAX(NOW() - submitted_at) FROM v_timesheets_canonical {where_clause} AND status = 'submitted'"
    max_age = await conn.fetchval(q5, *params)
    oldest_pending_days = max_age.days if max_age is not None else None

    return ApprovalQueueSummaryResponse(
        pending_count=pending_count,
        approved_this_week=approved_this_week,
        rejected_this_week=rejected_this_week,
        avg_hours_approved=avg_hours_approved,
        oldest_pending_days=oldest_pending_days,
    )


@router.post("/{timesheet_id}/approve", response_model=TimesheetResponse)
async def approve_timesheet(
    timesheet_id: UUID,
    body: ApproveTimesheetRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    """Approve a submitted timesheet."""
    _check_superadmin_or_manager(current_user)
    user_id = _parse_uuid(current_user.get("id"))
    org_id = _parse_uuid(current_user.get("organization_id"))

    has_access = await conn.fetchval(
        "SELECT fn_check_timesheet_approver_access($1, $2)",
        user_id,
        timesheet_id,
    )
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have approver access for this timesheet",
        )

    client_ip = request.client.host if request.client and request.client.host != "testclient" else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "")

    try:
        await conn.fetchrow(
            "SELECT * FROM fn_approve_timesheet($1, $2, $3, $4::inet, $5)",
            timesheet_id,
            user_id,
            body.comment,
            client_ip,
            user_agent,
        )
    except Exception as e:
        _handle_db_exception(e)

    updated_row = await conn.fetchrow(
        "SELECT * FROM v_timesheets_canonical WHERE id = $1 AND org_id = $2",
        timesheet_id,
        org_id,
    )
    if not updated_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found after approval",
        )

    week_label = f"Week of {updated_row['week_start_date']}"
    await notify_timesheet_approved(
        conn=conn,
        timesheet_id=timesheet_id,
        submitter_id=updated_row["user_id"],
        approver_id=user_id,
        week_label=week_label,
    )

    return TimesheetResponse.model_validate(dict(updated_row))


@router.post("/{timesheet_id}/reject", response_model=TimesheetResponse)
async def reject_timesheet(
    timesheet_id: UUID,
    body: RejectTimesheetRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    """Reject a submitted timesheet with mandatory comment (reverts to draft)."""
    _check_superadmin_or_manager(current_user)
    user_id = _parse_uuid(current_user.get("id"))
    org_id = _parse_uuid(current_user.get("organization_id"))

    if not body.comment or not body.comment.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Comment is mandatory for rejecting a timesheet",
        )

    has_access = await conn.fetchval(
        "SELECT fn_check_timesheet_approver_access($1, $2)",
        user_id,
        timesheet_id,
    )
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have approver access for this timesheet",
        )

    client_ip = request.client.host if request.client and request.client.host != "testclient" else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "")

    try:
        await conn.fetchrow(
            "SELECT * FROM fn_reject_timesheet($1, $2, $3, $4::inet, $5)",
            timesheet_id,
            user_id,
            body.comment.strip(),
            client_ip,
            user_agent,
        )
    except Exception as e:
        _handle_db_exception(e)

    updated_row = await conn.fetchrow(
        "SELECT * FROM v_timesheets_canonical WHERE id = $1 AND org_id = $2",
        timesheet_id,
        org_id,
    )
    if not updated_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found after rejection",
        )

    week_label = f"Week of {updated_row['week_start_date']}"
    await notify_timesheet_rejected(
        conn=conn,
        timesheet_id=timesheet_id,
        submitter_id=updated_row["user_id"],
        approver_id=user_id,
        week_label=week_label,
        comment=body.comment.strip(),
    )

    return TimesheetResponse.model_validate(dict(updated_row))

