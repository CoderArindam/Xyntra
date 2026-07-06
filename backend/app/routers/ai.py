import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.database.connection import get_db_connection
from app.auth.dependencies import get_current_user
from app.schemas.ai import AIChatRequest
from app.services.ai_service import AIService, check_rate_limit
from app.config.config import settings

router = APIRouter(
    prefix="/ai",
    tags=["ai"]
)

@router.post("/chat")
async def chat_endpoint(
    request: AIChatRequest,
    fastapi_req: Request,
    current_user: dict = Depends(get_current_user),
    conn = Depends(get_db_connection)
):
    if not settings.AI_ENABLED:
        raise HTTPException(status_code=403, detail="AI features are disabled.")
        
    check_rate_limit(current_user["id"])
        
    ai_service = AIService(conn)
    request_id = str(uuid.uuid4())
    
    # We return a StreamingResponse that yields chunks
    # We pass fastapi_req to let the service handle cancellation if needed
    return StreamingResponse(
        ai_service.chat_stream(request, current_user, request_id),
        media_type="text/event-stream"
    )
