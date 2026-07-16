"""Speaker Mapping Stage."""

from typing import List, Type

from app.meeting.artifacts.base import MeetingArtifact
from app.meeting.artifacts.speaker import SpeakerTimeline, ParticipantRoster, SpeakerMapping
from app.meeting.pipeline.context import PipelineContext
from app.meeting.pipeline.stage import PipelineStage, StageStatus
from app.meeting.mapping.service import SpeakerMappingService

class SpeakerMappingStage(PipelineStage):
    """Maps anonymous speakers to real participants."""

    @property
    def stage_name(self) -> str:
        return "SpeakerMappingStage"

    @property
    def execution_order(self) -> int:
        return 800

    @property
    def required_artifacts(self) -> List[Type[MeetingArtifact]]:
        return [SpeakerTimeline, ParticipantRoster]

    @property
    def generated_artifacts(self) -> List[Type[MeetingArtifact]]:
        return [SpeakerMapping]

    @property
    def retryable(self) -> bool:
        return False

    @property
    def continue_on_failure(self) -> bool:
        return False

    async def execute(self, context: PipelineContext) -> StageStatus:
        timeline = context.artifacts.get(SpeakerTimeline)
        roster = context.artifacts.get(ParticipantRoster)
        
        if not timeline or not roster:
            return StageStatus.FAILED
            
        service = SpeakerMappingService()
        
        try:
            mapping = await service.build(timeline, roster)
            if not mapping or not mapping.entries:
                context.warnings.append("Speaker mapping failed: empty mapping")
                return StageStatus.FAILED
                
            context.artifacts.register(mapping)
            return StageStatus.SUCCESS
        except Exception as e:
            context.warnings.append(f"Speaker mapping failed: {str(e)}")
            return StageStatus.FAILED
