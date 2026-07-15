"""SpeakerMappingService — Orchestrates identity resolution mapping."""

from typing import Optional

from app.meeting.artifacts.speaker import (
    ParticipantRoster,
    SpeakerMapping,
    SpeakerTimeline,
)
from app.meeting.config import meeting_config
from app.meeting.exceptions import SpeakerMappingError
from app.meeting.logger import get_logger
from .registry import MappingStrategyRegistry

log = get_logger("attribution.mapping")


class SpeakerMappingService:
    """Produces a SpeakerMapping artifact from diarization and roster data.

    Fetches the configured mapping strategy from the registry and delegates
    the deterministic resolution logic.
    """

    async def build(
        self,
        timeline: SpeakerTimeline,
        roster: Optional[ParticipantRoster],
    ) -> SpeakerMapping:
        log.info(
            "attribution.mapping.started",
            meeting_id=timeline.meeting_id,
            timeline_id=timeline.id,
            roster_id=roster.id if roster else None,
            speaker_count=timeline.speaker_count,
            strategy=meeting_config.MAPPING_STRATEGY,
        )

        try:
            strategy = MappingStrategyRegistry.get(meeting_config.MAPPING_STRATEGY)
            artifact = await strategy.build_mapping(timeline, roster)

        except SpeakerMappingError:
            log.error(
                "attribution.mapping.failed",
                meeting_id=timeline.meeting_id,
            )
            raise
        except Exception as exc:
            log.error(
                "attribution.mapping.failed",
                meeting_id=timeline.meeting_id,
                error=str(exc),
            )
            raise SpeakerMappingError(f"Speaker mapping failed: {exc}") from exc

        log.info(
            "attribution.mapping.completed",
            meeting_id=timeline.meeting_id,
            artifact_id=artifact.id,
            resolved=artifact.resolved_count,
            unresolved=artifact.unresolved_count,
            duration_ms=artifact.mapping_duration_ms,
        )
        log.info(
            "meeting.artifact.generated",
            artifact_type="SpeakerMapping",
            artifact_id=artifact.id,
            meeting_id=timeline.meeting_id,
        )

        return artifact
