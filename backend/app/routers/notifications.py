import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from app.auth.dependencies import get_current_user
from app.database.connection import get_db_connection
from app.schemas.notifications import MarkBatchReadRequest, CanonicalNotificationResponse
from app.schemas.envelope import DataEnvelope
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Notifications"])


def get_notification_service(conn = Depends(get_db_connection)) -> NotificationService:
    return NotificationService(conn)

@router.get("/notifications", response_model=DataEnvelope[List[CanonicalNotificationResponse]])
async def get_notifications(
    cursor: Optional[int] = Query(None, description="Cursor for pagination (id)"),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    notifications, meta = await notification_service.get_notifications(cursor, limit, current_user)
    return DataEnvelope(data=notifications, meta=meta)

@router.patch("/notifications/{notification_id}/read", status_code=204)
async def mark_read(
    notification_id: int,
    current_user: dict = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    await notification_service.mark_read(notification_id, current_user)
    return None

@router.patch("/notifications/read-batch", status_code=204)
async def mark_batch_read(
    payload: MarkBatchReadRequest,
    current_user: dict = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    await notification_service.mark_batch_read(payload, current_user)
    return None

@router.patch("/notifications/read-all", status_code=204)
async def mark_all_read(
    current_user: dict = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    await notification_service.mark_all_read(current_user)
    return None

@router.delete("/notifications/{notification_id}", status_code=204)
async def delete_notification(
    notification_id: int,
    current_user: dict = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    await notification_service.delete_notification(notification_id, current_user)
    return None
