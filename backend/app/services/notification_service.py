from app.services.email_service import send_email
from app.services.email_templates import (
    task_assigned_template,
    task_assignment_changed_template,
    task_status_changed_template,
    task_comment_added_template
)
import logging

logger = logging.getLogger(__name__)

def dispatch_task_email(
    activity_type: str,
    task_title: str,
    board_name: str,
    actor_name: str,
    assignee_email: str = None,
    assignee_name: str = None,
    old_assignee_email: str = None,
    old_assignee_name: str = None,
    old_status: str = None,
    new_status: str = None,
    comment: str = None
):
    """
    Dispatches appropriate emails based on the activity.
    Should be called via FastAPI BackgroundTasks so it doesn't block the API.
    """
    try:
        if activity_type == "ASSIGNEE_CHANGED":
            if assignee_email:
                subject = "You have been assigned a task"
                body = task_assigned_template(task_title, board_name, actor_name)
                send_email(assignee_email, subject, body)
                
            if old_assignee_email and old_assignee_email != assignee_email:
                subject = "Task assignment updated"
                body = task_assignment_changed_template(task_title, assignee_name or assignee_email)
                send_email(old_assignee_email, subject, body)

        elif activity_type == "STATUS_CHANGED":
            if assignee_email:
                subject = f"Task status updated to {new_status}"
                body = task_status_changed_template(task_title, old_status, new_status, actor_name)
                send_email(assignee_email, subject, body)
                
        elif activity_type == "DUE_DATE_CHANGED":
            if assignee_email:
                subject = "Task due date updated"
                # using assignment changed template as a fallback since no specific template exists for due dates,
                # but standard practice is just reuse a generic update or create one.
                # Actually, let's just send a simple text email if there's no template
                body = f"Hi {assignee_name or 'there'},\n\nThe due date for the task '{task_title}' was updated by {actor_name}.\n\nThanks,\nThe Team"
                send_email(assignee_email, subject, body)

        elif activity_type == "COMMENT_ADDED":
            if assignee_email:
                subject = "New comment on your task"
                body = task_comment_added_template(task_title, actor_name, comment or "")
                send_email(assignee_email, subject, body)

    except Exception as e:
        logger.error(f"Failed to dispatch email notification for {activity_type}: {e}")

import asyncpg
from fastapi import HTTPException
from typing import List, Optional
from app.schemas.notifications import MarkBatchReadRequest, CanonicalNotificationResponse
from app.schemas.envelope import MetaResponse

class NotificationService:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def get_notifications(self, cursor: Optional[int], limit: int, current_user: dict):
        try:
            query = "SELECT * FROM v_notifications_canonical WHERE user_id = $1"
            args = [current_user["id"]]
            
            if cursor is not None:
                query += " AND id < $2"
                args.append(cursor)
                
            args.append(limit + 1)
            query += f" ORDER BY id DESC LIMIT ${len(args)}"
            
            rows = await self.conn.fetch(query, *args)
            
            has_more = len(rows) > limit
            notifications = rows[:limit]
            
            next_cursor = str(notifications[-1]["id"]) if notifications else None
            
            return [CanonicalNotificationResponse(**dict(row)) for row in notifications], MetaResponse(cursor=next_cursor, has_more=has_more)
        except Exception as e:
            logger.error(f"Error fetching notifications: {e}")
            raise HTTPException(status_code=500, detail="An error occurred while fetching notifications")

    async def mark_read(self, notification_id: int, current_user: dict):
        try:
            await self.conn.execute(
                "UPDATE notifications SET is_read = true WHERE id = $1 AND user_id = $2",
                notification_id, current_user["id"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail="Failed to mark notification as read")

    async def mark_unread(self, notification_id: int, current_user: dict):
        try:
            await self.conn.execute(
                "UPDATE notifications SET is_read = false WHERE id = $1 AND user_id = $2",
                notification_id, current_user["id"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail="Failed to mark notification as unread")

    async def mark_batch_read(self, payload: MarkBatchReadRequest, current_user: dict):
        if not payload.notification_ids:
            return
        try:
            await self.conn.execute(
                "UPDATE notifications SET is_read = true WHERE user_id = $1 AND id = ANY($2::int[])",
                current_user["id"], payload.notification_ids
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail="Failed to mark notifications as read")

    async def mark_all_read(self, current_user: dict):
        try:
            await self.conn.execute(
                "UPDATE notifications SET is_read = true WHERE user_id = $1 AND is_read = false",
                current_user["id"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail="Failed to mark all notifications as read")

    async def delete_notification(self, notification_id: int, current_user: dict):
        try:
            await self.conn.execute(
                "DELETE FROM notifications WHERE id = $1 AND user_id = $2",
                notification_id, current_user["id"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail="Failed to delete notification")
