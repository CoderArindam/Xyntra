import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import get_current_user
from app.database.connection import get_db_connection
from app.schemas.activity import CanonicalActivityResponse
from app.schemas.envelope import DataEnvelope
from app.services.activity_service import ActivityService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Activity"])


def get_activity_service(conn = Depends(get_db_connection)) -> ActivityService:
    return ActivityService(conn)

@router.get("/tasks/{task_id}/activity", response_model=DataEnvelope[List[CanonicalActivityResponse]])
async def get_task_activity_endpoint(
    task_id: int,
    cursor: Optional[int] = Query(None, description="Cursor for pagination (id)"),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    activity_service: ActivityService = Depends(get_activity_service)
):
    activities, meta = await activity_service.get_task_activity(task_id, cursor, limit, current_user)
    return DataEnvelope(data=activities, meta=meta)
