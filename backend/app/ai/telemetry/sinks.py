import logging
import json
from enum import IntEnum
from typing import Dict, Any, List
from .events import TelemetryEvent, EventType

class LogLevel(IntEnum):
    OFF = 0
    ERROR = 1
    INFO = 2
    DEBUG = 3
    TRACE = 4

class TelemetrySink:
    def process_event(self, event: TelemetryEvent):
        pass

class ConsoleLoggerSink(TelemetrySink):
    def __init__(self, level: LogLevel = LogLevel.INFO):
        self.level = level
        self.logger = logging.getLogger("ai.telemetry")
        # Ensure the logger actually prints
        if not self.logger.handlers:
            ch = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)
        self.logger.setLevel(logging.INFO)

        # Internal state to build the execution tree for TRACE level
        self._request_trees: Dict[str, Dict[str, Any]] = {}
        
    def process_event(self, event: TelemetryEvent):
        if self.level == LogLevel.OFF:
            return

        if event.event_type == EventType.ERROR_OCCURRED and self.level >= LogLevel.ERROR:
            self._log_error(event)
            return

        if self.level >= LogLevel.TRACE:
            self._build_tree(event)

        # DEBUG level logic: log major events
        if self.level >= LogLevel.DEBUG:
            if event.event_type in [
                EventType.SPAN_COMPLETED,
                EventType.LLM_CALL_COMPLETED,
                EventType.TOOL_EXECUTION_COMPLETED,
                EventType.RETRY_OCCURRED
            ]:
                self.logger.info(f"[DEBUG] {event.event_type.value}: {json.dumps(event.metadata)}")

        # INFO level logic: log request summaries
        if self.level >= LogLevel.INFO:
            if event.event_type == EventType.REQUEST_COMPLETED:
                self._log_summary(event)

    def _log_error(self, event: TelemetryEvent):
        self.logger.error(f"[ERROR] {event.metadata.get('message', 'Unknown Error')} | Component: {event.metadata.get('component')} | Exception: {event.metadata.get('exception_type')}")

    def _log_summary(self, event: TelemetryEvent):
        metrics = event.metadata
        summary = (
            f"\n=== AI Request Summary ===\n"
            f"Request ID: {event.request_id}\n"
            f"Execution ID: {event.execution_id}\n"
            f"Duration: {metrics.get('duration_ms', 0)}ms\n"
            f"Total LLM Calls: {metrics.get('total_llm_calls', 0)}\n"
            f"Total Tokens: {metrics.get('total_tokens', 0)}\n"
            f"Tools Executed: {metrics.get('tools_executed', 0)}\n"
            f"Services Invoked: {metrics.get('services_invoked', 0)}\n"
            f"Retries: {metrics.get('total_retries', 0)}\n"
            f"Status: {metrics.get('status', 'unknown')}\n"
            f"=========================="
        )
        self.logger.info(summary)
        
        # If TRACE is on, print the tree when the request completes
        if self.level >= LogLevel.TRACE and event.request_id in self._request_trees:
            self._print_tree(event.request_id)
            del self._request_trees[event.request_id]

    def _build_tree(self, event: TelemetryEvent):
        req_id = event.request_id
        if not req_id:
            return
            
        if req_id not in self._request_trees:
            self._request_trees[req_id] = {"spans": {}, "root_spans": []}
            
        tree = self._request_trees[req_id]
        
        if event.event_type == EventType.SPAN_STARTED:
            span_data = {
                "id": event.span_id,
                "name": event.metadata.get("name"),
                "component": event.metadata.get("component"),
                "children": [],
                "details": []
            }
            tree["spans"][event.span_id] = span_data
            
            if event.parent_span_id and event.parent_span_id in tree["spans"]:
                tree["spans"][event.parent_span_id]["children"].append(span_data)
            else:
                tree["root_spans"].append(span_data)
                
        elif event.event_type == EventType.SPAN_COMPLETED:
            if event.span_id in tree["spans"]:
                tree["spans"][event.span_id]["duration_ms"] = event.metadata.get("duration_ms")
                tree["spans"][event.span_id]["status"] = event.metadata.get("status")
                
        elif event.event_type in [EventType.LLM_CALL_COMPLETED, EventType.TOOL_EXECUTION_COMPLETED, EventType.SERVICE_EXECUTION_COMPLETED, EventType.RETRY_OCCURRED]:
            # Attach detail to current active span
            if event.span_id and event.span_id in tree["spans"]:
                tree["spans"][event.span_id]["details"].append(event)

    def _print_tree(self, req_id: str):
        tree = self._request_trees.get(req_id)
        if not tree:
            return
            
        lines = [f"\n=== Execution Timeline (Request: {req_id}) ==="]
        
        def render_node(node, prefix=""):
            duration = node.get("duration_ms", "?")
            status = node.get("status", "")
            status_str = f" [{status}]" if status != "success" else ""
            lines.append(f"{prefix}├── {node['name']} ({duration}ms){status_str}")
            
            # Print details
            detail_prefix = prefix + "│   "
            for detail in node["details"]:
                if detail.event_type == EventType.LLM_CALL_COMPLETED:
                    lines.append(f"{detail_prefix}├── LLM Call: {detail.metadata.get('provider')}/{detail.metadata.get('model')} - {detail.metadata.get('prompt_id')} ({detail.metadata.get('duration_ms')}ms, {detail.metadata.get('total_tokens')} tokens)")
                elif detail.event_type == EventType.RETRY_OCCURRED:
                    lines.append(f"{detail_prefix}├── RETRY: {detail.metadata.get('reason')}")
                    
            for i, child in enumerate(node["children"]):
                is_last = (i == len(node["children"]) - 1)
                new_prefix = prefix + ("    " if is_last else "│   ")
                render_node(child, prefix + "│   ")
                
        for root in tree["root_spans"]:
            render_node(root)
            
        self.logger.info("\n".join(lines))
