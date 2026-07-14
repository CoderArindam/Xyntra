from typing import List, Optional
from .base import MeetingArtifact


class TranscriptSegment(MeetingArtifact):
    """An individual spoken segment."""
    timestamp_start: float
    timestamp_end: float
    speaker: Optional[str] = None
    detected_language: str = "unknown"
    confidence: float
    text: str


class SpeakerSegment(MeetingArtifact):
    """Diarization output mapping a speaker to a time window."""
    timestamp_start: float
    timestamp_end: float
    speaker_label: str
    confidence: float


class RawTranscript(MeetingArtifact):
    """Initial speech-to-text output before normalization."""
    segments: List[TranscriptSegment]
    provider: str


class NormalizedTranscript(MeetingArtifact):
    """Transcript that has been cleaned of hallucinations and mapped correctly."""
    segments: List[TranscriptSegment]


class MeetingTranscript(MeetingArtifact):
    """The final canonical transcript, merging diarization and normalization."""
    segments: List[TranscriptSegment]
    language: str
