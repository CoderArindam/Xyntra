import json
from pathlib import Path
from typing import Optional

from app.meeting.artifacts.speaker import ParticipantPresenceTimeline
from app.meeting.contracts.participant_presence_provider import ParticipantPresenceProvider


class JsonPresenceProvider(ParticipantPresenceProvider):
    """Loads a ParticipantPresenceTimeline from the local filesystem."""

    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def collect(self, meeting_id: str, **kwargs) -> ParticipantPresenceTimeline:
        """Fetch the timeline from a local JSON file."""
        timeline_path = self.storage_dir / meeting_id / "participant_presence_timeline.json"

        if not timeline_path.exists():
            # Fallback or return empty timeline
            return ParticipantPresenceTimeline(
                meeting_id=meeting_id,
                meeting_started_at="",
                timeline_started_at="",
                events=[],
                current_snapshot=[],
                processing_version="1.0.0"
            )

        with open(timeline_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return ParticipantPresenceTimeline.model_validate(data)
