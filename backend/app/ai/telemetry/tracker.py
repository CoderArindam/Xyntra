import logging
from typing import Any, Dict, Optional
import time

logger = logging.getLogger("ai.telemetry")
logger.setLevel(logging.INFO)

class TelemetryEvent:
    def __init__(
        self,
        provider: str,
        model: str,
        workflow_id: Optional[str] = None,
        request_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        self.provider = provider
        self.model = model
        self.workflow_id = workflow_id
        self.request_id = request_id
        self.conversation_id = conversation_id
        self.organization_id = organization_id
        self.user_id = user_id
        
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.estimated_cost = 0.0
        self.retries = 0
        self.tool_calls = 0
        self.success = False
        self.cancelled = False
        self.error: Optional[str] = None

    def record_success(self, prompt_tokens: int, completion_tokens: int, estimated_cost: float = 0.0):
        self.end_time = time.time()
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.estimated_cost = estimated_cost
        self.success = True
        self.log()

    def record_failure(self, error: str):
        self.end_time = time.time()
        self.success = False
        self.error = error
        self.log()
        
    def record_cancelled(self, prompt_tokens: int = 0, completion_tokens: int = 0):
        self.end_time = time.time()
        self.success = False
        self.cancelled = True
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.log()
        
    def add_retry(self):
        self.retries += 1
        
    def add_tool_call(self):
        self.tool_calls += 1

    def _build_payload(self) -> Dict[str, Any]:
        latency_ms = int((self.end_time - self.start_time) * 1000) if self.end_time else None
        return {
            "type": "ai_telemetry",
            "provider": self.provider,
            "model": self.model,
            "workflow_id": self.workflow_id,
            "request_id": self.request_id,
            "conversation_id": self.conversation_id,
            "organization_id": self.organization_id,
            "user_id": self.user_id,
            "latency_ms": latency_ms,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "estimated_cost": self.estimated_cost,
            "retries": self.retries,
            "tool_calls": self.tool_calls,
            "success": self.success,
            "cancelled": self.cancelled,
            "error": self.error,
        }

    def log(self):
        payload = self._build_payload()
        if self.success:
            logger.info("AI Request Completed", extra=payload)
        elif self.cancelled:
            logger.info("AI Request Cancelled", extra=payload)
        else:
            logger.error(f"AI Request Failed: {self.error}", extra=payload)

class ToolTelemetryTracker:
    @staticmethod
    def record_tool_execution(tool_name: str, latency: float, success: bool, error: Optional[str] = None, agent_name: Optional[str] = None):
        payload = {
            "type": "ai_tool_telemetry",
            "tool_name": tool_name,
            "agent_name": agent_name,
            "latency_ms": int(latency * 1000),
            "success": success,
            "error": error
        }
        if success:
            logger.info(f"Tool {tool_name} Executed Successfully", extra=payload)
        else:
            logger.error(f"Tool {tool_name} Failed: {error}", extra=payload)

# Global tracker for tool telemetry
tool_telemetry = ToolTelemetryTracker()
