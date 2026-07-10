import json
from typing import Any, Dict


SSE_VERSION = "1.0"


def sse_event(event_type: str, **kwargs) -> str:
    """Format a single SSE data line with standard versioning."""
    payload: Dict[str, Any] = {"v": SSE_VERSION, "type": event_type, **kwargs}
    return f"data: {json.dumps(payload)}\n\n"


def sse_message_start(execution_id: str) -> str:
    return sse_event("assistant_message_start", execution_id=execution_id)


def sse_message_chunk(content: str) -> str:
    return sse_event("assistant_message_chunk", content=content)


def sse_message_end() -> str:
    return sse_event("assistant_message_end")


def sse_error(error: str, details: str = None) -> str:
    payload = {"error": error}
    if details:
        payload["details"] = details
    return sse_event("error", **payload)
