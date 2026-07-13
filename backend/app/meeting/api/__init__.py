"""Meeting API endpoints."""

from app.meeting.api.router import router, _service as meeting_service

__all__ = ["router", "meeting_service"]
