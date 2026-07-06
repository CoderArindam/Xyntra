from fastapi import APIRouter, Depends
from app.schemas.attachments import AttachmentCreate
from app.auth.dependencies import get_current_user
from app.database.connection import get_db_connection
from app.services.attachment_service import AttachmentService

router = APIRouter(tags=["Attachments"])

def get_attachment_service(conn = Depends(get_db_connection)) -> AttachmentService:
    return AttachmentService(conn)

@router.post("/tasks/{task_id}/attachments")
async def create_attachment(
    task_id: int,
    attachment_in: AttachmentCreate,
    current_user: dict = Depends(get_current_user),
    attachment_service: AttachmentService = Depends(get_attachment_service)
):
    result = await attachment_service.create_attachment(task_id, attachment_in, current_user)
    return result

@router.get("/tasks/{task_id}/attachments")
async def get_task_attachments(
    task_id: int,
    current_user: dict = Depends(get_current_user),
    attachment_service: AttachmentService = Depends(get_attachment_service)
):
    result = await attachment_service.get_task_attachments(task_id, current_user)
    return result
