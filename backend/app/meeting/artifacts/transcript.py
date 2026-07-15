from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import Field

from .base import MeetingArtifact


class TranscriptSegment(MeetingArtifact):
    """An individual spoken segment from STT output."""

    id: str
    start_time: float
    end_time: float
    text: str

    # Raw Whisper / provider-specific metrics
    avg_logprob: float
    no_speech_probability: float
    compression_ratio: float

    # Derived/abstract metrics
    confidence: Optional[float] = None
    speaker: Optional[str] = None
    detected_language: str = "unknown"


class SpeakerSegment(MeetingArtifact):
    """Diarization output mapping a speaker to a time window."""

    timestamp_start: float
    timestamp_end: float
    speaker_label: str
    confidence: float


class RawTranscript(MeetingArtifact):
    """Initial speech-to-text output before normalization."""

    parent_processed_audio_id: str
    detected_language: str
    language_probability: float
    model_name: str
    transcription_started_at: str
    transcription_completed_at: str
    transcription_duration_ms: int
    segments: List[TranscriptSegment]
    overall_confidence: Optional[float] = None
    processing_version: str


# ---------------------------------------------------------------------------
# Normalized layer — provider-independent, no STT-specific fields
# ---------------------------------------------------------------------------


class NormalizedTranscriptSegment(MeetingArtifact):
    """A cleaned, provider-independent transcript segment.

    Whisper-specific fields (avg_logprob, compression_ratio, etc.) are
    intentionally absent — they belong only in TranscriptSegment.
    """

    id: str
    start_time: float
    end_time: float
    text: str
    speaker: Optional[str] = None
    language: str = "unknown"
    confidence: Optional[float] = None
    word_count: int = 0
    character_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NormalizationStatistics(MeetingArtifact):
    """Per-rule and aggregate normalization stats for observability.

    rule_statistics keys correspond to rule names.  New rules add new keys
    without schema changes.
    """

    rule_statistics: Dict[str, int] = Field(default_factory=dict)
    total_input_segments: int = 0
    total_output_segments: int = 0
    removed_segments: int = 0
    merged_segments: int = 0
    processing_time_ms: int = 0
    average_segment_length: float = 0.0


class NormalizedTranscript(MeetingArtifact):
    """Deterministically cleaned transcript produced by the normalization pipeline.

    Consumes: RawTranscript
    Produces:  NormalizedTranscript  (this artifact)
    Never mutates the parent RawTranscript.
    """

    parent_raw_transcript_id: str
    language: str
    processing_version: str
    normalization_started_at: str
    normalization_completed_at: str
    normalization_duration_ms: int
    segments: List[NormalizedTranscriptSegment]
    statistics: NormalizationStatistics


class MeetingTranscript(MeetingArtifact):
    """The final canonical transcript, merging diarization and normalization."""

    segments: List[TranscriptSegment]
    language: str
