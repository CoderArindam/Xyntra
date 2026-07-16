"""Participant Resolution Stage."""

from typing import List, Type

from app.meeting.artifacts.base import MeetingArtifact
from app.meeting.artifacts.speaker import SpeakerAttributedTranscript, SpeakerMapping, ParticipantAttributedTranscript
from app.meeting.pipeline.context import PipelineContext
from app.meeting.pipeline.stage import PipelineStage, StageStatus
from app.meeting.attribution.service import SpeakerAttributionService

class ParticipantResolutionStage(PipelineStage):
    """Resolves anonymous speakers in the transcript to real participants."""

    @property
    def stage_name(self) -> str:
        return "ParticipantResolutionStage"

    @property
    def execution_order(self) -> int:
        return 900

    @property
    def required_artifacts(self) -> List[Type[MeetingArtifact]]:
        return [SpeakerAttributedTranscript, SpeakerMapping]

    @property
    def generated_artifacts(self) -> List[Type[MeetingArtifact]]:
        return [ParticipantAttributedTranscript]

    @property
    def retryable(self) -> bool:
        return False

    @property
    def continue_on_failure(self) -> bool:
        return False

    async def execute(self, context: PipelineContext) -> StageStatus:
        attributed = context.artifacts.get(SpeakerAttributedTranscript)
        mapping = context.artifacts.get(SpeakerMapping)
        
        if not attributed or not mapping:
            return StageStatus.FAILED
            
        service = SpeakerAttributionService()
        
        try:
            participant_attributed = await service.resolve(attributed, mapping)
            context.artifacts.register(participant_attributed)
            return StageStatus.SUCCESS
        except Exception as e:
            context.warnings.append(f"Participant resolution failed: {str(e)}")
            return StageStatus.FAILED
