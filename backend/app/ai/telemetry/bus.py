from typing import List
from .events import TelemetryEvent, EventType
from .sinks import TelemetrySink

class EventBus:
    def __init__(self):
        self.sinks: List[TelemetrySink] = []

    def register_sink(self, sink: TelemetrySink):
        self.sinks.append(sink)

    def publish(self, event_type: EventType, **kwargs):
        event = TelemetryEvent(event_type=event_type, **kwargs)
        for sink in self.sinks:
            try:
                sink.process_event(event)
            except Exception as e:
                # We don't want telemetry failures to break the application
                import logging
                logging.getLogger("ai.telemetry").error(f"Telemetry sink failed: {str(e)}")

# Global Singleton Event Bus
telemetry_bus = EventBus()
