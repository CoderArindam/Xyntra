"""Pipeline execution context and artifact registry."""

from typing import Dict, Optional, Type, Any, TypeVar, List
from pydantic import BaseModel, Field
from datetime import datetime
import json
from pathlib import Path

from app.meeting.artifacts.base import MeetingArtifact

TArtifact = TypeVar("TArtifact", bound=MeetingArtifact)

class ArtifactRegistry:
    """Manages persistence and retrieval of meeting artifacts."""
    
    def __init__(self, session_directory: Path):
        self.session_directory = session_directory
        self._cache: Dict[str, MeetingArtifact] = {}
        
    def _get_artifact_path(self, artifact_type: Type[TArtifact]) -> Path:
        """Map artifact types to standard filenames."""
        # Simple mapping convention based on snake_case class names or explicit map
        # E.g. SpeakerAttributedTranscript -> speaker_attributed_transcript.json
        name = artifact_type.__name__
        snake = ''.join(['_'+c.lower() if c.isupper() else c for c in name]).lstrip('_')
        
        # A few special cases where artifact names don't exactly match the type name
        overrides = {
            "processed_audio": "processed_audio.json",
            "speaker_timeline": "speaker_timeline.json",
            "participant_roster": "participant_roster.json",
            "speaker_mapping": "speaker_mapping.json",
            "speaker_attributed_transcript": "speaker_attributed_transcript.json",
            "participant_attributed_transcript": "participant_attributed_transcript.json",
            "participant_presence_timeline": "participant_presence_timeline.json",
            "normalized_transcript": "normalized_transcript.json",
            "attribution_debug_artifact": "attribution_debug.json",
            "attribution_timeline_artifact": "attribution_timeline.json",
            # Assuming raw transcript from Whisper
            "raw_transcript": "raw_transcript_v1.json" 
        }
        
        filename = overrides.get(snake, f"{snake}.json")
        return self.session_directory / filename
        
    def register(self, artifact: MeetingArtifact) -> None:
        """Save artifact to disk and register in cache."""
        artifact_type = type(artifact)
        path = self._get_artifact_path(artifact_type)
        
        path.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
        self._cache[artifact_type.__name__] = artifact
        
    def get(self, artifact_type: Type[TArtifact]) -> Optional[TArtifact]:
        """Retrieve artifact from cache or disk."""
        type_name = artifact_type.__name__
        
        if type_name in self._cache:
            return self._cache[type_name]
            
        path = self._get_artifact_path(artifact_type)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                artifact = artifact_type.model_validate(data)
                self._cache[type_name] = artifact
                return artifact
            except Exception:
                return None
                
        return None
        
    def exists(self, artifact_type: Type[TArtifact]) -> bool:
        """Check if an artifact is fully generated."""
        return self.get(artifact_type) is not None


class PipelineContext(BaseModel):
    """Context passed through all pipeline stages."""
    
    meeting_id: str
    session_directory: Path
    processing_version: str = "1.0.0"
    
    artifacts: ArtifactRegistry = Field(exclude=True)
    
    # Execution state
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    completed_at: Optional[str] = None
    completed_stages: List[str] = Field(default_factory=list)
    skipped_stages: List[str] = Field(default_factory=list)
    failed_stage: Optional[str] = None
    
    events: List[Any] = Field(default_factory=list)
    
    diagnostics: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True
