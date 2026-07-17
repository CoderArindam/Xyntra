"""Speech processing observability metrics.

SpeechProcessingMetrics collects all fields required by the logging
specification and produces a structured dict for log emission and
future dashboard ingestion.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class SpeechProcessingMetrics:
    """All observability fields for a single speech processing request."""

    request_id: str
    meeting_id: str
    provider: str
    model: str

    # Timing (set via start/stop helpers)
    _start_time: float = field(default_factory=time.monotonic, repr=False, compare=False)
    provider_latency_ms: Optional[int] = None   # time spent waiting on the provider API
    total_duration_ms: Optional[int] = None     # total processing time (upload + wait + normalize)

    # Audio
    audio_duration_seconds: Optional[float] = None

    # Transcript quality
    transcript_duration_seconds: Optional[float] = None
    detected_language: Optional[str] = None
    language_confidence: Optional[float] = None
    word_count: int = 0
    speaker_count: int = 0
    confidence: Optional[float] = None

    # Retry
    retry_count: int = 0

    # Failure (set on error path)
    failure_reason: Optional[str] = None
    error_type: Optional[str] = None
    success: bool = False

    def mark_provider_start(self) -> None:
        self._provider_start = time.monotonic()

    def mark_provider_end(self) -> None:
        if hasattr(self, "_provider_start"):
            self.provider_latency_ms = int((time.monotonic() - self._provider_start) * 1000)

    def mark_complete(self, success: bool = True) -> None:
        self.total_duration_ms = int((time.monotonic() - self._start_time) * 1000)
        self.success = success

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "meeting_id": self.meeting_id,
            "provider": self.provider,
            "model": self.model,
            "audio_duration_seconds": self.audio_duration_seconds,
            "provider_latency_ms": self.provider_latency_ms,
            "total_duration_ms": self.total_duration_ms,
            "transcript_duration_seconds": self.transcript_duration_seconds,
            "detected_language": self.detected_language,
            "language_confidence": self.language_confidence,
            "word_count": self.word_count,
            "speaker_count": self.speaker_count,
            "confidence": self.confidence,
            "retry_count": self.retry_count,
            "success": self.success,
            "failure_reason": self.failure_reason,
            "error_type": self.error_type,
        }
