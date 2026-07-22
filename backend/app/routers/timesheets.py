import logging
import uuid
from datetime import date
from typing import List, Optional
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.auth.dependencies import get_current_user
from app.routers.timesheet_errors import handle_timesheet_db_error
from app.database.connection import get_db_connection
from app.services.notification_service import notify_timesheet_submitted, notify_timesheet_recalled
from app.schemas.timesheets import (
    CreateTimesheetRequest,
    RecallTimesheetRequest,
    SubmitTimesheetRequest,
    TimesheetDetailResponse,
    TimesheetEntryResponse,
    TimesheetResponse,
    UpsertTimesheetEntryRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/timesheets", tags=["Timesheets"])


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



def _handle_db_exception(e: Exception):
    logger.warning(f"Database operation exception in timesheets router: {e}")
    handle_timesheet_db_error(e)


@router.get("", response_model=List[TimesheetResponse])
async def list_timesheets(
    status_filter: Optional[str] = Query(None, alias="status"),
    week_start_date: Optional[date] = Query(None),
    target_user_id: Optional[UUID] = Query(None, alias="user_id"),
    scope: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    """List timesheets based on strictly enforced role-based visibility rules."""
    user_id = _parse_uuid(current_user.get("id"))
    org_id = _parse_uuid(current_user.get("organization_id"))
    role = str(current_user.get("role") or "").lower()

    args = [org_id]

    if target_user_id and str(target_user_id) != str(user_id):
        if role in ("superadmin", "super_admin"):
            args.append(target_user_id)
            query = f"SELECT * FROM v_timesheets_canonical WHERE org_id = $1 AND user_id = $2"
        elif role == "manager":
            args.append(target_user_id)
            args.append(user_id)
            query = (
                f"SELECT * FROM v_timesheets_canonical WHERE org_id = $1 AND user_id = $2 "
                f"AND id IN (SELECT fn_get_manager_accessible_timesheet_ids($3, $1))"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view timesheets for other users",
            )
    elif scope == "all":
        if role in ("superadmin", "super_admin"):
            query = "SELECT * FROM v_timesheets_canonical WHERE org_id = $1"
        elif role == "manager":
            args.append(user_id)
            query = (
                f"SELECT * FROM v_timesheets_canonical WHERE org_id = $1 "
                f"AND id IN (SELECT fn_get_manager_accessible_timesheet_ids($2, $1))"
            )
        else:
            args.append(user_id)
            query = f"SELECT * FROM v_timesheets_canonical WHERE org_id = $1 AND user_id = $2"
    else:
        # Default for "My Timesheets": filter strictly by the logged-in user
        args.append(user_id)
        query = f"SELECT * FROM v_timesheets_canonical WHERE org_id = $1 AND user_id = $2"

    if status_filter:
        args.append(status_filter)
        query += f" AND status = ${len(args)}"

    if week_start_date:
        args.append(week_start_date)
        query += f" AND week_start_date = ${len(args)}"

    query += " ORDER BY week_start_date DESC LIMIT 52"

    rows = await conn.fetch(query, *args)
    return [TimesheetResponse.model_validate(dict(r)) for r in rows]


@router.post("", response_model=TimesheetResponse, status_code=status.HTTP_201_CREATED)
async def create_timesheet(
    body: CreateTimesheetRequest,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    """Create a new draft timesheet for the authenticated user for the target week."""
    user_id = _parse_uuid(current_user.get("id"))
    org_id = _parse_uuid(current_user.get("organization_id"))

    existing = await conn.fetchval(
        "SELECT id FROM v_timesheets_canonical WHERE user_id = $1 AND org_id = $2 AND week_start_date = $3",
        user_id,
        org_id,
        body.week_start_date,
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A timesheet already exists for this week",
        )

    try:
        ts_row = await conn.fetchrow(
            "SELECT * FROM fn_create_timesheet($1, $2, $3)",
            user_id,
            org_id,
            body.week_start_date,
        )
    except Exception as e:
        _handle_db_exception(e)

    if not ts_row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create timesheet",
        )

    ts_id = ts_row["id"]
    canonical_row = await conn.fetchrow(
        "SELECT * FROM v_timesheets_canonical WHERE id = $1 AND org_id = $2",
        ts_id,
        org_id,
    )

    if not canonical_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found after creation",
        )

    return TimesheetResponse.model_validate(dict(canonical_row))


@router.get("/{timesheet_id}", response_model=TimesheetDetailResponse)
async def get_timesheet_detail(
    timesheet_id: UUID,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    """Retrieve complete timesheet detail with entries and audit log."""
    user_id = _parse_uuid(current_user.get("id"))
    org_id = _parse_uuid(current_user.get("organization_id"))
    role = str(current_user.get("role") or "").lower()

    ts_row = await conn.fetchrow(
        "SELECT * FROM v_timesheets_canonical WHERE id = $1 AND org_id = $2",
        timesheet_id,
        org_id,
    )
    if not ts_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found",
        )

    if str(ts_row["user_id"]) == str(user_id):
        # Timesheet owner can ALWAYS view their own timesheet regardless of role
        pass
    else:
        # Non-owners (including Super Admin and other Managers): must be verified via fn_check_timesheet_approver_access
        has_access = await conn.fetchval(
            "SELECT fn_check_timesheet_approver_access($1, $2)",
            user_id,
            timesheet_id,
        )
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You do not have approver access to this timesheet",
            )

    entries_rows = await conn.fetch(
        "SELECT * FROM v_timesheet_entries_canonical WHERE timesheet_id = $1 ORDER BY entry_date, created_at",
        timesheet_id,
    )
    audit_rows = await conn.fetch(
        "SELECT * FROM v_timesheet_audit_canonical WHERE timesheet_id = $1 ORDER BY created_at",
        timesheet_id,
    )

    detail_dict = dict(ts_row)
    detail_dict["entries"] = [dict(r) for r in entries_rows]
    detail_dict["audit_log"] = [dict(r) for r in audit_rows]

    return TimesheetDetailResponse.model_validate(detail_dict)


@router.post("/{timesheet_id}/entries", response_model=TimesheetEntryResponse, status_code=status.HTTP_201_CREATED)
async def upsert_timesheet_entry(
    timesheet_id: UUID,
    body: UpsertTimesheetEntryRequest,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    """Add or update an entry on a draft timesheet (owner only)."""
    user_id = _parse_uuid(current_user.get("id"))
    org_id = _parse_uuid(current_user.get("organization_id"))

    ts_row = await conn.fetchrow(
        "SELECT user_id FROM v_timesheets_canonical WHERE id = $1 AND org_id = $2",
        timesheet_id,
        org_id,
    )
    if not ts_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found",
        )
    if ts_row["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only the owner can modify entries for this timesheet",
        )

    if body.task_id and (not body.entry_type or body.entry_type == "task"):
        task_row = await conn.fetchrow(
            """
            SELECT assigned_to FROM v_tasks_canonical
            WHERE (id::text = $1 OR LTRIM(RIGHT(id::text, 12), '0') = LTRIM(RIGHT($1, 12), '0'))
              AND (organization_id::text = $2 OR LTRIM(RIGHT(organization_id::text, 12), '0') = LTRIM(RIGHT($2, 12), '0'))
            """,
            str(body.task_id),
            str(org_id),
        )
        if not task_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "TASK_NOT_FOUND", "detail": "The specified task was not found."},
            )
        if _parse_uuid(task_row["assigned_to"]) != user_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error_code": "TASK_NOT_ASSIGNED", "detail": "Time can only be logged against tasks assigned to you."},
            )

    try:
        entry_row = await conn.fetchrow(
            """
            SELECT * FROM fn_upsert_timesheet_entry(
                $1, $2, $3, $4, $5, $6, $7, $8
            )
            """,
            timesheet_id,
            user_id,
            body.board_id,
            body.task_id,
            body.entry_date,
            body.hours,
            body.entry_type,
            body.description,
        )
    except Exception as e:
        _handle_db_exception(e)

    if not entry_row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to upsert timesheet entry",
        )

    entry_id = entry_row["id"]
    canonical_entry = await conn.fetchrow(
        "SELECT * FROM v_timesheet_entries_canonical WHERE id = $1",
        entry_id,
    )
    if not canonical_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet entry not found after upsert",
        )

    return TimesheetEntryResponse.model_validate(dict(canonical_entry))


@router.delete("/{timesheet_id}/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_timesheet_entry(
    timesheet_id: UUID,
    entry_id: UUID,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    """Delete an entry from a draft timesheet (owner only)."""
    user_id = _parse_uuid(current_user.get("id"))
    org_id = _parse_uuid(current_user.get("organization_id"))

    ts_row = await conn.fetchrow(
        "SELECT user_id FROM v_timesheets_canonical WHERE id = $1 AND org_id = $2",
        timesheet_id,
        org_id,
    )
    if not ts_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found",
        )
    if ts_row["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only the owner can delete entries from this timesheet",
        )

    try:
        await conn.fetchval(
            "SELECT fn_delete_timesheet_entry($1, $2)",
            entry_id,
            user_id,
        )
    except Exception as e:
        _handle_db_exception(e)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{timesheet_id}/submit", response_model=TimesheetResponse)
async def submit_timesheet(
    timesheet_id: UUID,
    body: SubmitTimesheetRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    """Submit a draft timesheet for approval (owner only)."""
    user_id = _parse_uuid(current_user.get("id"))
    org_id = _parse_uuid(current_user.get("organization_id"))

    ts_row = await conn.fetchrow(
        "SELECT user_id FROM v_timesheets_canonical WHERE id = $1 AND org_id = $2",
        timesheet_id,
        org_id,
    )
    if not ts_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found",
        )
    if ts_row["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only the owner can submit this timesheet",
        )

    client_ip = request.client.host if request.client and request.client.host != "testclient" else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "")

    try:
        await conn.fetchrow(
            """
            SELECT * FROM fn_submit_timesheet($1, $2, $3, $4::inet, $5, $6)
            """,
            timesheet_id,
            user_id,
            body.member_note,
            client_ip,
            user_agent,
            body.approver_id,
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
            detail="Timesheet not found after submission",
        )

    week_label = f"Week of {updated_row['week_start_date']}"
    submitter_name = updated_row.get("submitter_name") or current_user.get("first_name") or current_user.get("email")
    await notify_timesheet_submitted(
        conn=conn,
        timesheet_id=timesheet_id,
        submitter_id=user_id,
        approver_id=updated_row.get("approver_id"),
        week_label=week_label,
        submitter_name=submitter_name,
    )

    return TimesheetResponse.model_validate(dict(updated_row))


@router.post("/{timesheet_id}/recall", response_model=TimesheetResponse)
async def recall_timesheet(
    timesheet_id: UUID,
    body: RecallTimesheetRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    """Recall a submitted timesheet back to draft status (owner only)."""
    user_id = _parse_uuid(current_user.get("id"))
    org_id = _parse_uuid(current_user.get("organization_id"))

    ts_row = await conn.fetchrow(
        "SELECT user_id, approver_id FROM v_timesheets_canonical WHERE id = $1 AND org_id = $2",
        timesheet_id,
        org_id,
    )
    if not ts_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found",
        )
    if ts_row["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only the owner can recall this timesheet",
        )

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")

    try:
        await conn.fetchrow(
            """
            SELECT * FROM fn_recall_timesheet($1, $2, $3, $4::inet, $5)
            """,
            timesheet_id,
            user_id,
            body.reason,
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
            detail="Timesheet not found after recall",
        )

    week_label = f"Week of {updated_row['week_start_date']}"
    submitter_name = updated_row.get("submitter_name") or current_user.get("first_name") or current_user.get("email")
    await notify_timesheet_recalled(
        conn=conn,
        timesheet_id=timesheet_id,
        submitter_id=user_id,
        approver_id=ts_row.get("approver_id") or updated_row.get("approver_id"),
        week_label=week_label,
        reason=body.reason,
        submitter_name=submitter_name,
    )

    return TimesheetResponse.model_validate(dict(updated_row))

