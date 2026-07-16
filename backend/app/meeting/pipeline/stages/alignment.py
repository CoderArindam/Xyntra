"""Speaker Alignment Stage."""

from typing import List, Type

from app.meeting.artifacts.base import MeetingArtifact
from app.meeting.artifacts.speaker import SpeakerTimeline, SpeakerAttributedTranscript
from app.meeting.artifacts.transcript import NormalizedTranscript
from app.meeting.pipeline.context import PipelineContext
from app.meeting.pipeline.stage import PipelineStage, StageStatus
from app.meeting.alignment.service import SpeakerAlignmentService

class SpeakerAlignmentStage(PipelineStage):
    """Aligns speaker turns with normalized transcript segments."""

    @property
    def stage_name(self) -> str:
        return "SpeakerAlignmentStage"

    @property
    def execution_order(self) -> int:
        return 500

    @property
    def required_artifacts(self) -> List[Type[MeetingArtifact]]:
        return [NormalizedTranscript, SpeakerTimeline]

    @property
    def generated_artifacts(self) -> List[Type[MeetingArtifact]]:
        return [SpeakerAttributedTranscript]

    @property
    def retryable(self) -> bool:
        return False

    @property
    def continue_on_failure(self) -> bool:
        return False

    async def execute(self, context: PipelineContext) -> StageStatus:
        transcript = context.artifacts.get(NormalizedTranscript)
        timeline = context.artifacts.get(SpeakerTimeline)
        
        if not transcript or not timeline:
            return StageStatus.FAILED
            
        service = SpeakerAlignmentService()
        
        try:
            attributed = await service.align(transcript, timeline)
            context.artifacts.register(attributed)
            return StageStatus.SUCCESS
        except Exception as e:
            context.warnings.append(f"Alignment failed: {str(e)}")
            return StageStatus.FAILED
