import logging
import uuid
from typing import List, Optional
import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.task_proposal import (
    TaskProposalOut,
    TaskProposalUpdateIn,
    TaskProposalApproveIn,
    TaskProposalRejectIn,
)
from app.schemas.task import CanonicalTaskResponse
from app.schemas.envelope import DataEnvelope
from app.auth.dependencies import require_proposal_review_access
from app.database.connection import get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Task Proposals"])


@router.get("/proposals", response_model=DataEnvelope[List[TaskProposalOut]])
async def list_organization_task_proposals(
    status: Optional[str] = "pending",
    current_user: dict = Depends(require_proposal_review_access),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """List all task proposals for the current user's organization."""
    org_id = current_user["organization_id"]

    query = """
        SELECT * FROM v_task_proposals_canonical
        WHERE org_id = $1
    """
    args = [org_id]

    if status:
        query += " AND status = $2"
        args.append(status)

    query += " ORDER BY confidence_score DESC NULLS LAST, created_at DESC"

    rows = await conn.fetch(query, *args)
    proposals = [TaskProposalOut.model_validate(dict(row)) for row in rows]
    return DataEnvelope(data=proposals)


@router.get("/meeting/{session_id}/proposals", response_model=DataEnvelope[List[TaskProposalOut]])
async def list_meeting_task_proposals(
    session_id: str,
    current_user: dict = Depends(require_proposal_review_access),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """List all AI-extracted task proposals for a given meeting session, ordered by confidence score."""
    org_id = current_user["organization_id"]

    try:
        target_uuid = await conn.fetchval(
            "SELECT id FROM meeting_sessions WHERE (id::text = $1 OR session_id = $1) AND org_id = $2",
            session_id, org_id
        )

        rows = await conn.fetch(
            """
            SELECT * FROM v_task_proposals_canonical
            WHERE (meeting_session_id::text = $1 OR meeting_session_id = $2) AND org_id = $3
            ORDER BY confidence_score DESC NULLS LAST, created_at DESC
            """,
            session_id,
            target_uuid or uuid.UUID(session_id),
            org_id
        )
    except Exception:
        rows = await conn.fetch(
            "SELECT * FROM v_task_proposals_canonical WHERE meeting_session_id::text = $1 AND org_id = $2 ORDER BY created_at DESC",
            session_id, org_id
        )

    proposals = [TaskProposalOut.model_validate(dict(row)) for row in rows]
    return DataEnvelope(data=proposals)


@router.get("/proposals/{id}", response_model=DataEnvelope[TaskProposalOut])
async def get_task_proposal_detail(
    id: uuid.UUID,
    current_user: dict = Depends(require_proposal_review_access),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """Get detailed information for a single task proposal."""
    org_id = current_user["organization_id"]

    row = await conn.fetchrow(
        """
        SELECT * FROM v_task_proposals_canonical
        WHERE id = $1 AND org_id = $2
        """,
        id,
        org_id
    )

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task proposal not found"
        )

    return DataEnvelope(data=TaskProposalOut.model_validate(dict(row)))


@router.put("/proposals/{id}", response_model=DataEnvelope[TaskProposalOut])
async def update_task_proposal(
    id: uuid.UUID,
    body: TaskProposalUpdateIn,
    current_user: dict = Depends(require_proposal_review_access),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """Edit title, description, suggested assignee, or target board for a pending proposal."""
    assignee_val = body.suggested_assignee_id if body.suggested_assignee_id is not None else -1
    board_id_val = body.board_id if body.board_id is not None else None

    try:
        updated_row = await conn.fetchrow(
            """
            SELECT * FROM fn_update_task_proposal(
                $1::uuid,
                $2::text,
                $3::text,
                $4::integer,
                $5::integer,
                $6::text,
                $7::timestamptz
            )
            """,
            id,
            body.title,
            body.description,
            assignee_val,
            board_id_val,
            body.priority,
            body.due_date
        )
    except Exception as e:
        err_msg = str(e)
        if "must be pending" in err_msg or "status is" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot edit proposal: status is not pending"
            )
        elif "not found" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task proposal not found"
            )
        logger.error(f"Error updating task proposal: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update proposal")

    if not updated_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task proposal not found")

    # Return canonical view payload
    row = await conn.fetchrow(
        "SELECT * FROM v_task_proposals_canonical WHERE id = $1::uuid",
        id
    )
    return DataEnvelope(data=TaskProposalOut.model_validate(dict(row)))


@router.post("/proposals/{id}/approve", response_model=DataEnvelope[CanonicalTaskResponse])
async def approve_task_proposal(
    id: uuid.UUID,
    body: Optional[TaskProposalApproveIn] = None,
    current_user: dict = Depends(require_proposal_review_access),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """Atomically approve a proposal and create the corresponding Kanban task card, accepting an optional board_id override."""
    user_id = current_user["id"]
    board_id_override = body.board_id if body and body.board_id is not None else None

    try:
        created_task = await conn.fetchrow(
            """
            SELECT * FROM fn_approve_task_proposal($1, $2::integer, $3::integer)
            """,
            id,
            user_id,
            board_id_override
        )
    except Exception as e:
        err_msg = str(e)
        if "without an assigned board" in err_msg or "Cannot approve a task proposal without an assigned board" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error_code": "BOARD_REQUIRED",
                    "message": "Cannot approve a task proposal without an assigned board. Please select a board before approving."
                }
            )
        elif "must be pending" in err_msg or "status is" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot approve proposal: status is not pending"
            )
        elif "not found" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task proposal not found"
            )
        logger.error(f"Error approving task proposal: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to approve proposal")


    if not created_task:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to create task from proposal")

    # Fetch canonical task view item
    task_id = created_task["id"]
    canonical_row = await conn.fetchrow(
        "SELECT * FROM v_tasks_canonical WHERE id = $1",
        task_id
    )

    if not canonical_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Created task card not found")

    return DataEnvelope(data=CanonicalTaskResponse(**dict(canonical_row)))


@router.post("/proposals/{id}/reject", response_model=DataEnvelope[TaskProposalOut])
async def reject_task_proposal(
    id: uuid.UUID,
    body: Optional[TaskProposalRejectIn] = None,
    current_user: dict = Depends(require_proposal_review_access),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """Reject a pending task proposal."""
    user_id = current_user["id"]

    try:
        rejected_row = await conn.fetchrow(
            """
            SELECT * FROM fn_reject_task_proposal($1::uuid, $2::integer)
            """,
            id,
            user_id
        )
    except Exception as e:
        err_msg = str(e)
        if "must be pending" in err_msg or "status is" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot reject proposal: status is not pending"
            )
        elif "not found" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task proposal not found"
            )
        logger.error(f"Error rejecting task proposal: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to reject proposal")

    if not rejected_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task proposal not found")

    # Return canonical view representation
    row = await conn.fetchrow(
        "SELECT * FROM v_task_proposals_canonical WHERE id = $1::uuid",
        id
    )
    return DataEnvelope(data=TaskProposalOut.model_validate(dict(row)))


@router.get("/boards/{board_id}/proposals", response_model=DataEnvelope[List[TaskProposalOut]])
async def list_pending_board_proposals(
    board_id: int,
    current_user: dict = Depends(require_proposal_review_access),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """List all pending task proposals across a board's meetings."""
    org_id = current_user["organization_id"]

    rows = await conn.fetch(
        """
        SELECT * FROM v_task_proposals_canonical
        WHERE (board_id = $1 OR board_id IS NULL) AND org_id = $2 AND status = 'pending'
        ORDER BY created_at DESC
        """,
        board_id,
        org_id
    )

    proposals = [TaskProposalOut.model_validate(dict(row)) for row in rows]
    return DataEnvelope(data=proposals)
