"""JSON participant roster provider for development mode."""

import json
from pathlib import Path

from app.meeting.artifacts.speaker import ParticipantRoster
from app.meeting.config import meeting_config
from app.meeting.contracts.participant_roster_provider import ParticipantRosterProvider
from app.meeting.exceptions import MeetingError


class JsonParticipantRosterProvider(ParticipantRosterProvider):
    """Loads a ParticipantRoster from the local filesystem."""

    async def get_roster(self, meeting_id: str, **kwargs) -> ParticipantRoster:
        processed_dir = Path(meeting_config.PROCESSING_OUTPUT_DIR) / meeting_id
        roster_path = processed_dir / "participant_roster.json"

        if not roster_path.exists():
            raise MeetingError(
                code="ROSTER_NOT_FOUND",
                message=f"No participant_roster.json found for {meeting_id} in {processed_dir}",
                recoverable=False,
                retryable=False,
            )

        try:
            return ParticipantRoster.model_validate_json(roster_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise MeetingError(
                code="ROSTER_PARSE_ERROR",
                message=f"Failed to parse participant roster for {meeting_id}: {exc}",
                recoverable=False,
                retryable=False,
            ) from exc
