import logging
from typing import Optional

logger = logging.getLogger("ai.telemetry")
logger.setLevel(logging.INFO)

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

tool_telemetry = ToolTelemetryTracker()

