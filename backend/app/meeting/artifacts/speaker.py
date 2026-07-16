"""Speaker diarization and attribution artifact models.

Artifact hierarchy:
  ProcessedAudio
    ├── SpeakerTimeline        (diarization output — anonymous speakers)
    └── ParticipantRoster      (meeting platform participant list)

  NormalizedTranscript + SpeakerTimeline
    └── SpeakerAttributedTranscript  (text + Speaker_01 labels)

  SpeakerTimeline + ParticipantRoster
    └── SpeakerMapping               (Speaker_01 → participant identity)

  SpeakerAttributedTranscript + SpeakerMapping
    └── ParticipantAttributedTranscript  (text + real names)

Child objects (SpeakerTurn, MeetingParticipant, etc.) are plain Pydantic
BaseModel — not MeetingArtifact.  Only coarse-grained documents that are
stored and referenced across pipeline stages carry artifact overhead.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal, Union

from pydantic import BaseModel, Field

from .base import MeetingArtifact


# ---------------------------------------------------------------------------
# Value objects — plain BaseModel, no artifact overhead
# ---------------------------------------------------------------------------


class DiarizationProviderInfo(BaseModel):
    """Identity metadata for the diarization provider that produced an artifact."""

    provider_name: str      # "pyannote", "assemblyai", "nemo", "azure"
    provider_version: str   # "3.1.0"
    model_name: str         # "pyannote/speaker-diarization-3.1"


class SpeakerTurn(BaseModel):
    """One contiguous speaker region from diarization output.

    No text — only timing and speaker identity.
    embedding_id is None now; populated once voice fingerprinting is added.
    """

    speaker_label: str              # "Speaker_01" — immutable, never overwritten
    start_time: float               # seconds
    end_time: float                 # seconds
    diarization_confidence: float   # provider-reported confidence for this turn
    embedding_id: Optional[str] = None  # future: ref to voice embedding store


class MeetingParticipant(BaseModel):
    """A single participant identity captured from the meeting platform.

    No voice information.  No speaker labels.  Only identity.
    join_order is preserved for later first-speaker heuristics.
    """

    participant_id: str
    display_name: str
    email: Optional[str] = None
    join_time: str                  # ISO 8601
    leave_time: Optional[str] = None
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    join_order: int                 # 1-indexed arrival order in the meeting
    total_presence_duration: float = 0.0
    join_events: List[str] = Field(default_factory=list)
    leave_events: List[str] = Field(default_factory=list)
    is_host: bool = False
    is_guest: bool = False
    is_bot: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Presence Events (Raw Timeline)
# ---------------------------------------------------------------------------

class PresenceEvent(BaseModel):
    """Base class for all presence events."""
    event_id: str
    sequence_number: int
    timestamp: str                  # ISO 8601
    source: str                     # e.g., GOOGLE_MEET, JSON, MANUAL
    participant_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ParticipantJoined(PresenceEvent):
    event_type: Literal["ParticipantJoined"] = "ParticipantJoined"
    display_name: str


class ParticipantLeft(PresenceEvent):
    event_type: Literal["ParticipantLeft"] = "ParticipantLeft"


class ParticipantRenamed(PresenceEvent):
    event_type: Literal["ParticipantRenamed"] = "ParticipantRenamed"
    new_display_name: str


class HostTransferred(PresenceEvent):
    event_type: Literal["HostTransferred"] = "HostTransferred"
    new_host_id: str


class ParticipantRejoined(PresenceEvent):
    event_type: Literal["ParticipantRejoined"] = "ParticipantRejoined"
    display_name: str


AnyPresenceEvent = Union[
    ParticipantJoined,
    ParticipantLeft,
    ParticipantRenamed,
    HostTransferred,
    ParticipantRejoined,
]


class SpeakerMappingEntry(BaseModel):
    """Maps one anonymous speaker label to a real participant identity.

    participant_id / participant_name are nullable — a speaker may never be
    resolved in the current phase.  mapping_source tracks how the mapping
    was produced so future strategies (voice embedding, AI, manual) are
    distinguishable without schema changes.
    """

    speaker_label: str                  # "Speaker_01"
    participant_id: Optional[str] = None
    participant_name: Optional[str] = None
    mapping_confidence: float = 0.0
    mapping_source: str = "unknown"     # "unknown" | "join_order" | "voice_embedding"
                                        # | "ai_reasoning" | "manual"


class SpeakerAttributedSegment(BaseModel):
    """A transcript segment annotated with an anonymous speaker label.

    speaker_label comes from diarization — it is never a participant name.
    diarization_confidence  — reported by the diarization provider for the turn.
    attribution_confidence  — overlap ratio used when matching this segment to a turn.
    These two confidences represent distinct probabilities; never merge them.
    """

    segment_id: str
    start_time: float
    end_time: float
    text: str
    speaker_label: Optional[str] = None         # None if no turn matched
    diarization_confidence: Optional[float] = None
    attribution_confidence: Optional[float] = None
    language: str = "unknown"


class ParticipantAttributedSegment(BaseModel):
    """A transcript segment with both speaker label and resolved participant identity.

    speaker_label is always preserved — it is never replaced by participant_name.
    participant_* fields are nullable when resolution failed.
    """

    segment_id: str
    start_time: float
    end_time: float
    text: str
    speaker_label: Optional[str] = None         # "Speaker_01" — immutable
    speaker_label_confidence: Optional[float] = None
    participant_id: Optional[str] = None
    participant_name: Optional[str] = None
    mapping_confidence: Optional[float] = None
    language: str = "unknown"


# ---------------------------------------------------------------------------
# Artifacts — inherit MeetingArtifact (coarse-grained, stored documents)
# ---------------------------------------------------------------------------


class SpeakerTimeline(MeetingArtifact):
    """Ordered diarization output — who spoke when.

    Consumes:  ProcessedAudio
    Produces:  SpeakerTimeline (this artifact)

    Contains no text.  No participant names.  Only speaker regions.
    This artifact is independent of STT and participant collection.
    """

    parent_processed_audio_id: str
    provider: DiarizationProviderInfo
    speaker_count: int
    total_speech_duration_seconds: float
    turns: List[SpeakerTurn]
    diarization_started_at: str     # ISO 8601
    diarization_completed_at: str   # ISO 8601
    diarization_duration_ms: int
    processing_version: str


class ParticipantPresenceTimeline(MeetingArtifact):
    """Raw, immutable sequence of presence events during the meeting."""

    meeting_started_at: str
    recording_started_at: Optional[str] = None
    timeline_started_at: str
    events: List[AnyPresenceEvent] = Field(default_factory=list)
    current_snapshot: List[MeetingParticipant] = Field(default_factory=list)
    processing_version: str


class ParticipantRoster(MeetingArtifact):
    """Immutable snapshot of meeting participants reduced from the presence timeline.

    Consumes:  ParticipantPresenceTimeline
    Produces:  ParticipantRoster (this artifact)

    No voice information.  No speaker labels.  Only identity.
    Participants are ordered by join_order for downstream heuristics.
    """

    parent_presence_timeline_id: Optional[str] = None
    source: str                         # "google_meet" | "zoom" | "teams"
    participants: List[MeetingParticipant]
    captured_at: str                    # ISO 8601 — when the roster was finalized
    processing_version: str = "1.0.0"


class SpeakerMapping(MeetingArtifact):
    """Maps anonymous speaker labels to real participant identities.

    Consumes:  SpeakerTimeline + ParticipantRoster
    Produces:  SpeakerMapping (this artifact)

    This artifact is intentionally separate from transcript attribution.
    It can be regenerated via voice embeddings, AI, or manual correction
    without touching the transcript at all.

    In M2.5 all entries have participant_id=None and mapping_source="unknown".
    Future strategies plug in by changing mapping_source without schema changes.
    """

    parent_speaker_timeline_id: str
    parent_participant_roster_id: Optional[str] = None
    mapping_strategy: str = "unknown"   # current resolution strategy
    entries: List[SpeakerMappingEntry]
    
    # Resolution Statistics
    resolved_count: int = 0
    unresolved_count: int = 0
    participant_count: int = 0
    speaker_count: int = 0
    
    # Processing Metadata
    mapping_started_at: str             # ISO 8601
    mapping_completed_at: str           # ISO 8601
    mapping_duration_ms: int
    processing_version: str


class SpeakerAttributedTranscript(MeetingArtifact):
    """Transcript annotated with anonymous speaker labels (Stage 1 attribution).

    Consumes:  NormalizedTranscript + SpeakerTimeline
    Produces:  SpeakerAttributedTranscript (this artifact)

    Participant names are never stored here — only Speaker_01, Speaker_02…
    This artifact is the input to Stage 2 (ParticipantAttributedTranscript).
    """

    parent_normalized_transcript_id: str
    parent_speaker_timeline_id: Optional[str] = None
    segments: List[SpeakerAttributedSegment]
    unattributed_segment_count: int = 0
    attribution_started_at: str
    attribution_completed_at: str
    attribution_duration_ms: int
    processing_version: str


class ParticipantAttributedTranscript(MeetingArtifact):
    """Transcript with both anonymous speaker labels and resolved participant names.

    Consumes:  SpeakerAttributedTranscript + SpeakerMapping
    Produces:  ParticipantAttributedTranscript (this artifact)

    speaker_label is always preserved in every segment.
    participant_name is nullable — unresolved speakers remain Speaker_XX.
    This is the canonical final transcript for this pipeline phase.
    """

    parent_speaker_attributed_transcript_id: str
    parent_speaker_mapping_id: Optional[str] = None
    segments: List[ParticipantAttributedSegment]
    unresolved_speaker_count: int = 0
    resolution_started_at: str
    resolution_completed_at: str
    resolution_duration_ms: int
    processing_version: str
