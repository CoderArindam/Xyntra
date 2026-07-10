from typing import List, Optional
from fastapi import APIRouter, Depends, Query

from app.schemas.my_work import MyWorkSummaryResponse
from app.schemas.task import CanonicalTaskResponse
from app.schemas.envelope import DataEnvelope
from app.auth.dependencies import get_current_user
from app.database.connection import get_db_connection
from app.services.my_work_service import MyWorkService

router = APIRouter(tags=["My Work"])

def get_my_work_service(conn = Depends(get_db_connection)) -> MyWorkService:
    return MyWorkService(conn)

@router.get("/my-work/summary", response_model=DataEnvelope[MyWorkSummaryResponse])
async def get_my_work_summary(
    current_user: dict = Depends(get_current_user),
    my_work_service: MyWorkService = Depends(get_my_work_service)
):
    data = await my_work_service.get_my_work_summary(current_user)
    return DataEnvelope(data=data)

@router.get("/my-work/tasks", response_model=DataEnvelope[List[CanonicalTaskResponse]])
async def get_my_work_tasks(
    due: Optional[str] = Query('all', description="Filter by due date"),
    sort: Optional[str] = Query('due', description="Sort by field"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    my_work_service: MyWorkService = Depends(get_my_work_service)
):
    tasks = await my_work_service.get_my_work_tasks(due, sort, limit, offset, current_user)
    return DataEnvelope(data=tasks)
