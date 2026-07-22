"""Presence Collection Stage."""

from typing import List, Type

from app.meeting.artifacts.base import MeetingArtifact
from app.meeting.artifacts.speaker import ParticipantPresenceTimeline
from app.meeting.pipeline.context import PipelineContext
from app.meeting.pipeline.stage import PipelineStage, StageStatus
from app.meeting.presence.service import ParticipantPresenceService
from app.meeting.providers.participant_presence import get_presence_provider

class PresenceCollectionStage(PipelineStage):
    """Collects participant presence events for the meeting."""

    @property
    def stage_name(self) -> str:
        return "PresenceCollectionStage"

    @property
    def execution_order(self) -> int:
        return 600

    @property
    def required_artifacts(self) -> List[Type[MeetingArtifact]]:
        # Does not strictly require audio or transcripts, but it requires the meeting ID 
        # which is in context. We can require no artifacts, or just wait.
        return []

    @property
    def generated_artifacts(self) -> List[Type[MeetingArtifact]]:
        return [ParticipantPresenceTimeline]

    @property
    def retryable(self) -> bool:
        return True

    @property
    def continue_on_failure(self) -> bool:
        return False

    async def execute(self, context: PipelineContext) -> StageStatus:
        from app.meeting.legacy.json_provider import JsonPresenceProvider
        from app.meeting.config import meeting_config
        from pathlib import Path
        
        storage_dir = Path(meeting_config.RECORDING_OUTPUT_DIR)
        provider = JsonPresenceProvider(storage_dir)
        
        # Diagnostics
        from app.meeting.logger import get_logger
        log = get_logger("pipeline.presence")
        log.info("Pipeline provider instance (json_provider)", provider_id=id(provider))
        
        service = ParticipantPresenceService(provider)
        
        try:
            timeline = await service.collect(context.meeting_id)
            if not timeline or not timeline.events:
                context.warnings.append("Presence collection failed: empty timeline")
                return StageStatus.FAILED
                
            context.artifacts.register(timeline)
            log.info("ParticipantPresenceService collected timeline")
            return StageStatus.SUCCESS
        except Exception as e:
            context.warnings.append(f"Presence collection failed: {str(e)}")
            return StageStatus.FAILED
