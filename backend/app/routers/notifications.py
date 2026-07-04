import logging
import asyncpg
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from app.auth.dependencies import get_current_user
from app.database.connection import get_db_connection
from app.schemas.notifications import MarkBatchReadRequest, CanonicalNotificationResponse
from app.schemas.common import DataEnvelope, MetaResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Notifications"])

@router.get("/notifications", response_model=DataEnvelope[List[CanonicalNotificationResponse]])
async def get_notifications(
    cursor: Optional[int] = Query(None, description="Cursor for pagination (id)"),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        query = "SELECT * FROM v_notifications_canonical WHERE user_id = $1"
        args = [current_user["id"]]
        
        if cursor is not None:
            query += " AND id < $2"
            args.append(cursor)
            
        args.append(limit + 1)
        query += f" ORDER BY id DESC LIMIT ${len(args)}"
        
        rows = await conn.fetch(query, *args)
        
        has_more = len(rows) > limit
        notifications = rows[:limit]
        
        next_cursor = str(notifications[-1]["id"]) if notifications else None
        
        return DataEnvelope(
            data=[CanonicalNotificationResponse(**dict(row)) for row in notifications],
            meta=MetaResponse(cursor=next_cursor, has_more=has_more)
        )
    except Exception as e:
        logger.error(f"Error fetching notifications: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while fetching notifications")

@router.patch("/notifications/{notification_id}/read", status_code=204)
async def mark_read(
    notification_id: int,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        await conn.execute(
            "UPDATE notifications SET is_read = true WHERE id = $1 AND user_id = $2",
            notification_id, current_user["id"]
        )
        return None
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to mark notification as read")

@router.patch("/notifications/read-batch", status_code=204)
async def mark_batch_read(
    payload: MarkBatchReadRequest,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    if not payload.notification_ids:
        return None
    try:
        await conn.execute(
            "UPDATE notifications SET is_read = true WHERE user_id = $1 AND id = ANY($2::int[])",
            current_user["id"], payload.notification_ids
        )
        return None
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to mark notifications as read")

@router.patch("/notifications/read-all", status_code=204)
async def mark_all_read(
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        await conn.execute(
            "UPDATE notifications SET is_read = true WHERE user_id = $1 AND is_read = false",
            current_user["id"]
        )
        return None
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to mark all notifications as read")

@router.delete("/notifications/{notification_id}", status_code=204)
async def delete_notification(
    notification_id: int,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        await conn.execute(
            "DELETE FROM notifications WHERE id = $1 AND user_id = $2",
            notification_id, current_user["id"]
        )
        return None
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to delete notification")
