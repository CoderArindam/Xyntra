from typing import Optional
from .base import MeetingArtifact


class MeetingRecording(MeetingArtifact):
    """Immutable artifact representing a completed meeting audio recording.

    Raw audio bytes are never embedded here — only metadata and the
    storage URI reference. Downstream phases consume this artifact.
    """
    file_path: str                  # Absolute on-disk path
    storage_uri: str                # Abstract URI (file:// now; s3:// later)
    duration_seconds: float
    format: str                     # "webm", "wav", etc.
    sample_rate: int                # Hz — e.g. 48000
    channel_count: int
    codec: str                      # "opus", "pcm", etc.
    mime_type: str                  # "audio/webm;codecs=opus"
    file_size_bytes: int
    checksum_sha256: str            # Integrity check for downstream consumers
    recording_start_time: str       # ISO 8601
    recording_end_time: str         # ISO 8601
    recording_status: str           # "completed", "partial", "failed"


class AudioSegment(MeetingArtifact):
    """A sliced segment of the raw audio for processing."""
    start_time: float
    end_time: float
    file_path: str


class ProcessedAudio(MeetingArtifact):
    """Validated, normalized audio ready for downstream STT/diarization."""
    parent_recording_id: str        # Lineage: the MeetingRecording.id that produced this
    file_path: str                  # Absolute on-disk path
    storage_uri: str                # Abstract URI (file:// now; s3:// later)
    duration_seconds: float
    format: str                     # "wav"
    codec: str                      # "pcm_s16le"
    sample_rate: int                # Hz — canonical (e.g. 16000)
    channels: int
    bitrate: int                    # bits/sec
    file_size_bytes: int
    checksum_sha256: str
    processing_started_at: str      # ISO 8601
    processing_completed_at: str    # ISO 8601
    processing_duration_ms: int
    processing_version: str         # Semver for reproducibility
