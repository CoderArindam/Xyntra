import json
from pathlib import Path
from app.meeting.artifacts.speaker import ParticipantPresenceTimeline

class EventRecorder:
    """Persists ParticipantPresenceTimeline to disk after events are collected."""
    
    def __init__(self, storage_dir: Path, meeting_id: str):
        self.meeting_dir = storage_dir / meeting_id
        self.timeline_path = self.meeting_dir / "participant_presence_timeline.json"
        
    async def persist(self, timeline: ParticipantPresenceTimeline) -> None:
        """Writes the timeline safely to disk."""
        from app.meeting.logger import get_logger
        log = get_logger("presence.recorder")
        log.info("EventRecorder wrote event", meeting_id=timeline.meeting_id)
        
        self.meeting_dir.mkdir(parents=True, exist_ok=True)
        # Using a temporary file for atomic write is a good practice
        temp_path = self.timeline_path.with_suffix('.tmp')
        
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(timeline.model_dump_json(indent=2))
            
        temp_path.replace(self.timeline_path)
