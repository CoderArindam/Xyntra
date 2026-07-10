import contextvars
from typing import Optional
import uuid
import time
from .events import EventType
from .bus import telemetry_bus

_request_id = contextvars.ContextVar("request_id", default=None)
_execution_id = contextvars.ContextVar("execution_id", default=None)
_span_id = contextvars.ContextVar("span_id", default=None)
_request_state = contextvars.ContextVar("request_state", default=None)

class TraceContext:
    @staticmethod
    def get_request_id() -> Optional[str]:
        return _request_id.get()
        
    @staticmethod
    def set_request_id(req_id: str):
        _request_id.set(req_id)
        
    @staticmethod
    def get_execution_id() -> Optional[str]:
        return _execution_id.get()
        
    @staticmethod
    def set_execution_id(exec_id: str):
        _execution_id.set(exec_id)
        
    @staticmethod
    def get_span_id() -> Optional[str]:
        return _span_id.get()
        
    @staticmethod
    def set_span_id(span_id: str):
        _span_id.set(span_id)
        
    @staticmethod
    def get_state() -> dict:
        state = _request_state.get()
        if state is None:
            state = {
                "total_llm_calls": 0,
                "total_tokens": 0,
                "tools_executed": 0,
                "services_invoked": 0,
                "total_retries": 0,
                "start_time": time.time()
            }
            _request_state.set(state)
        return state
        
    @staticmethod
    def increment_metric(metric: str, value: int = 1):
        state = TraceContext.get_state()
        state[metric] = state.get(metric, 0) + value

class Span:
    """A context manager representing a single unit of work."""
    def __init__(self, name: str, component: str, metadata: dict = None):
        self.name = name
        self.component = component
        self.metadata = metadata or {}
        
        self.span_id = str(uuid.uuid4())
        self.parent_span_id = TraceContext.get_span_id()
        self.request_id = TraceContext.get_request_id()
        self.execution_id = TraceContext.get_execution_id()
        
        self.start_time = None
        self._token = None

    def __enter__(self):
        self.start_time = time.time()
        # Set this span as the current active span
        self._token = _span_id.set(self.span_id)
        
        # Emit SpanStarted
        telemetry_bus.publish(
            event_type=EventType.SPAN_STARTED,
            request_id=self.request_id,
            execution_id=self.execution_id,
            span_id=self.span_id,
            parent_span_id=self.parent_span_id,
            metadata={
                "name": self.name,
                "component": self.component,
                **self.metadata
            }
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        status = "failed" if exc_type else "success"
        
        metadata = {
            "name": self.name,
            "component": self.component,
            "duration_ms": int(duration * 1000),
            "status": status,
        }
        
        if exc_type:
            metadata["error"] = str(exc_val)
            metadata["error_type"] = exc_type.__name__
            telemetry_bus.publish(
                event_type=EventType.ERROR_OCCURRED,
                request_id=self.request_id,
                execution_id=self.execution_id,
                span_id=self.span_id,
                parent_span_id=self.parent_span_id,
                metadata={"component": self.component, "message": str(exc_val), "exception_type": exc_type.__name__}
            )
            TraceContext.get_state()["status"] = "failed"
            
        telemetry_bus.publish(
            event_type=EventType.SPAN_COMPLETED,
            request_id=self.request_id,
            execution_id=self.execution_id,
            span_id=self.span_id,
            parent_span_id=self.parent_span_id,
            metadata=metadata
        )
        
        # Restore previous span
        _span_id.reset(self._token)
