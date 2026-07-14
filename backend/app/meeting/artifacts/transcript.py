from typing import List, Optional
from .base import MeetingArtifact


class TranscriptSegment(MeetingArtifact):
    """An individual spoken segment."""
    id: str
    start_time: float
    end_time: float
    text: str
    
    # Raw Whisper Metrics
    avg_logprob: float
    no_speech_probability: float
    compression_ratio: float
    
    # Derived/Abstract Metrics
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


class NormalizedTranscript(MeetingArtifact):
    """Transcript that has been cleaned of hallucinations and mapped correctly."""
    segments: List[TranscriptSegment]


class MeetingTranscript(MeetingArtifact):
    """The final canonical transcript, merging diarization and normalization."""
    segments: List[TranscriptSegment]
    language: str
