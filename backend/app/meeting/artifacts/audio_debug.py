"""Audio Capture Observability and Debug Artifact Models (Phase 0X)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .base import MeetingArtifact


class AudioTrackMetadata(BaseModel):
    """Metadata for a single MediaStreamTrack (audio or video)."""
    id: str
    label: str
    kind: str
    enabled: bool
    muted: bool
    readyState: str
    settings: Dict[str, Any] = Field(default_factory=dict)
    constraints: Dict[str, Any] = Field(default_factory=dict)
    capabilities: Dict[str, Any] = Field(default_factory=dict)


class AudioGraphNodeInfo(BaseModel):
    """Metadata for an AudioNode in the Web Audio API graph."""
    node_type: str
    number_of_inputs: int
    number_of_outputs: int
    channel_count: int
    channel_count_mode: str


class AudioCaptureDebugArtifact(MeetingArtifact):
    """Deterministic observability artifact for browser audio capture (audio_capture_debug.json)."""
    capture_timestamp: str
    browser_version: str
    platform: str
    selected_mime_type: str
    number_of_audio_tracks: int
    number_of_video_tracks: int
    audio_tracks: List[AudioTrackMetadata] = Field(default_factory=list)
    video_tracks: List[AudioTrackMetadata] = Field(default_factory=list)
    audio_graph: List[AudioGraphNodeInfo] = Field(default_factory=list)
    display_surface: Optional[str] = None
    logical_surface: Optional[bool] = None
    cursor: Optional[str] = None
    device_id: Optional[str] = None
    group_id: Optional[str] = None
    processing_version: str = "1.0.0"
