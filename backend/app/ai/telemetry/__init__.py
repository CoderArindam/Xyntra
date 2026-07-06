import os
from .bus import telemetry_bus
from .sinks import ConsoleLoggerSink, LogLevel
from .context import Span, TraceContext
from .events import EventType

# Configure default sink based on environment variable
debug_mode = os.getenv("AI_DEBUG_MODE", "INFO").upper()
try:
    log_level = LogLevel[debug_mode]
except KeyError:
    log_level = LogLevel.INFO

console_sink = ConsoleLoggerSink(level=log_level)
telemetry_bus.register_sink(console_sink)

__all__ = ["telemetry_bus", "Span", "TraceContext", "EventType", "LogLevel"]
