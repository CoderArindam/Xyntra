import time
from .events import EventType
from .bus import telemetry_bus
from .context import TraceContext, _request_id, _execution_id, _span_id, _request_state

class RequestTracer:
    """Helper to start/stop request tracing without indentation changes."""
    def __init__(self, request_id: str, execution_id: str):
        self.request_id = request_id
        self.execution_id = execution_id
        self._tokens = {}
        self._ended = False
        
    def start(self):
        self._tokens["req"] = _request_id.set(self.request_id)
        self._tokens["exec"] = _execution_id.set(self.execution_id)
        self._tokens["span"] = _span_id.set(None)
        self._tokens["state"] = _request_state.set({
            "total_llm_calls": 0,
            "total_tokens": 0,
            "tools_executed": 0,
            "services_invoked": 0,
            "total_retries": 0,
            "start_time": time.time()
        })
        
        telemetry_bus.publish(
            event_type=EventType.REQUEST_STARTED,
            request_id=self.request_id,
            execution_id=self.execution_id,
            metadata={"start_time": time.time()}
        )
        
    def end(self, error: Exception = None):
        if self._ended:
            return
        self._ended = True
        if error:
            telemetry_bus.publish(
                event_type=EventType.ERROR_OCCURRED,
                request_id=self.request_id,
                execution_id=self.execution_id,
                metadata={"component": "Request", "message": str(error), "exception_type": error.__class__.__name__}
            )
            
        state = _request_state.get()
        if state:
            duration_ms = int((time.time() - state["start_time"]) * 1000)
            state["duration_ms"] = duration_ms
            state["status"] = "failed" if error else "success"
            
            telemetry_bus.publish(
                event_type=EventType.REQUEST_COMPLETED,
                request_id=self.request_id,
                execution_id=self.execution_id,
                metadata=state
            )
            
        _request_id.reset(self._tokens["req"])
        _execution_id.reset(self._tokens["exec"])
        _span_id.reset(self._tokens["span"])
        _request_state.reset(self._tokens["state"])
