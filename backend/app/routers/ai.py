import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.database.connection import get_db_connection
from app.auth.dependencies import get_current_user
from app.schemas.ai import AIChatRequest
from app.ai.services.chat_service import AIService
from app.ai.services.rate_limiter import check_rate_limit
from app.ai.config.settings import ai_settings

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
    if not ai_settings.AI_ENABLED:
        raise HTTPException(status_code=403, detail="AI features are disabled.")
        
    check_rate_limit(current_user["id"])
        
    ai_service = AIService(conn)
    request_id = str(uuid.uuid4())
    print('Current user from ai.py file', current_user)
    
    return StreamingResponse(
        ai_service.chat_stream(request, current_user, request_id),
        media_type="text/event-stream"
    )

