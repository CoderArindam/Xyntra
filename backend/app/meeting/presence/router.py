import hashlib
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, Header, Request
from pydantic import BaseModel, Field

from app.meeting.config import meeting_config
from app.meeting.providers.participant_presence import get_presence_provider
from app.meeting.providers.participant_presence.realtime_provider import RealtimePresenceProvider
from app.meeting.artifacts.speaker import (
    ParticipantJoined,
    ParticipantLeft,
    ParticipantRenamed,
    HostTransferred,
    ParticipantRejoined,
    PresenceEvent
)

router = APIRouter(prefix="/presence", tags=["presence"])

def verify_api_key(authorization: str = Header(None)):
    if not meeting_config.EXTENSION_API_KEY_HASH:
        return "dev-bypass"
        
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    token = authorization.split("Bearer ")[1]
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    if token_hash != meeting_config.EXTENSION_API_KEY_HASH:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return token

class RegisterRequest(BaseModel):
    extension_version: str

class RegisterResponse(BaseModel):
    extension_id: str
    server_time: str
    supported_schema: str = "1.0"

@router.post("/register", response_model=RegisterResponse)
async def register_extension(req: RegisterRequest, token: str = Depends(verify_api_key)):
    from datetime import datetime
    import uuid
    return RegisterResponse(
        extension_id=str(uuid.uuid4()),
        server_time=datetime.utcnow().isoformat() + "Z"
    )

class ExtensionEvent(BaseModel):
    schema_version: str
    extension_version: str
    event_type: str
    payload: Dict[str, Any]

class EventResponse(BaseModel):
    status: str
    event_id: str
    sequence_number: int
    server_timestamp: str

@router.post("/session/{session_id}/events", response_model=EventResponse)
async def receive_event(session_id: str, event: ExtensionEvent, token: str = Depends(verify_api_key)):
    from datetime import datetime, timezone
    from app.meeting.services.meeting_service import MeetingService
    from app.meeting.logger import get_logger
    from app.meeting.intelligence.models import MeetingEvent, EventType, EventCategory
    
    log = get_logger("presence.router")
    
    from app.meeting.services.registry import meeting_service
    
    session = meeting_service.get_session(session_id)
    if not session:
        session = meeting_service._session_manager.get_by_meeting_id(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        session_id = session.session_id
        
    provider = get_or_create_provider(session_id)
    from app.meeting.providers.participant_presence.external_provider import ExternalPresenceProvider
    if not isinstance(provider, (RealtimePresenceProvider, ExternalPresenceProvider)):
        raise HTTPException(status_code=400, detail="Backend not configured for real-time presence events")
        
    if not provider._is_collecting:
        await provider.start()

    log.info("Presence Router received event", event_type=event.event_type, provider_id=id(provider))

    payload = event.payload
    event_id = payload.get("event_id")
    participant_id = payload.get("participant_id")
    event_type = event.event_type
    
    if event_type == "Heartbeat":
        active_tabs = payload.get("active_tabs", 0)
        cs_connected = payload.get("content_script_connected", False)
        await provider.handle_heartbeat(
            timestamp=payload.get("timestamp"),
            active_tabs=active_tabs,
            content_script_connected=cs_connected
        )
        return EventResponse(
            status="accepted",
            event_id=event_id or "heartbeat",
            sequence_number=0,
            server_timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
    timestamp = payload.get("timestamp")
    source = "chrome_extension"
    
    if event_type == "ParticipantJoined":
        await provider.handle_join(event_id, participant_id, payload.get("display_name"), source, timestamp)
    elif event_type == "ParticipantLeft":
        await provider.handle_leave(event_id, participant_id, source, timestamp)
    elif event_type == "ParticipantRenamed":
        await provider.handle_rename(event_id, participant_id, payload.get("new_display_name"), source, timestamp)
    elif event_type == "HostTransferred":
        await provider.handle_host_transfer(event_id, payload.get("old_host_id"), payload.get("new_host_id"), source, timestamp)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown event_type: {event_type}")

    runtime = meeting_service._runtimes.get(session_id)
    if runtime and runtime.event_bus:
        mtg_event_type = None
        if event_type == "ParticipantJoined":
            mtg_event_type = EventType.PARTICIPANT_JOINED
        elif event_type == "ParticipantLeft":
            mtg_event_type = EventType.PARTICIPANT_LEFT
        elif event_type == "ParticipantRenamed":
            mtg_event_type = EventType.PARTICIPANT_UPDATED
            
        if mtg_event_type:
            await runtime.event_bus.emit(MeetingEvent(
                type=mtg_event_type,
                category=EventCategory.PARTICIPANT,
                source="realtime_provider",
                payload={"participant_id": participant_id}
            ))

    return EventResponse(
        status="accepted",
        event_id=event_id,
        sequence_number=provider._sequence_counter,
        server_timestamp=datetime.utcnow().isoformat() + "Z"
    )

@router.get("/session/{session_id}/health")
async def health(session_id: str, token: str = Depends(verify_api_key)):
    from app.meeting.services.registry import meeting_service
    
    session = meeting_service.get_session(session_id)
    if not session:
        session = meeting_service._session_manager.get_by_meeting_id(session_id)
        if session:
            session_id = session.session_id

    provider = get_or_create_provider(session_id)
    if not isinstance(provider, RealtimePresenceProvider):
        return {"status": "inactive", "message": "External provider not configured"}
        
    last_hb = provider.last_heartbeat_at.isoformat() + "Z" if provider.last_heartbeat_at else None
    
    return {
        "extension_connected": provider.last_heartbeat_at is not None,
        "last_heartbeat": last_hb,
        "queued_events": len(provider._events),
        "backend_receiver_alive": True
    }

def get_or_create_provider(session_id: str):
    from app.meeting.providers.participant_presence import get_presence_provider
    from app.meeting.providers.participant_presence.recorder import EventRecorder
    provider = get_presence_provider(meeting_id=session_id)
    # For validation we attach a mock recorder or ensure it saves to a specific path
    # Let's attach an EventRecorder if it doesn't have one
    if not provider.recorder:
        from app.meeting.config import meeting_config
        from pathlib import Path
        provider.recorder = EventRecorder(Path(meeting_config.RECORDING_OUTPUT_DIR), session_id)
    return provider

