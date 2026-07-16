"""Meeting API endpoints."""

from app.meeting.api.router import router
from app.meeting.services.registry import meeting_service

__all__ = ["router", "meeting_service"]
