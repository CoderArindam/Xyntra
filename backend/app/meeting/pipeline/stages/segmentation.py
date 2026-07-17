"""Conversation Turn Segmentation Stage."""

from typing import List, Type

from app.meeting.artifacts.base import MeetingArtifact
from app.meeting.artifacts.transcript import NormalizedTranscript
from app.meeting.pipeline.context import PipelineContext
from app.meeting.pipeline.stage import PipelineStage, StageStatus
from app.meeting.segmentation.service import ConversationTurnSegmenter


class ConversationSegmentationStage(PipelineStage):
    """Splits merged multi-speaker transcript segments before alignment/attribution."""

    @property
    def stage_name(self) -> str:
        return "ConversationSegmentationStage"

    @property
    def execution_order(self) -> int:
        return 400

    @property
    def required_artifacts(self) -> List[Type[MeetingArtifact]]:
        return [NormalizedTranscript]

    @property
    def generated_artifacts(self) -> List[Type[MeetingArtifact]]:
        return [NormalizedTranscript]

    @property
    def retryable(self) -> bool:
        return False

    @property
    def continue_on_failure(self) -> bool:
        return False

    async def execute(self, context: PipelineContext) -> StageStatus:
        transcript = context.artifacts.get(NormalizedTranscript)
        if not transcript:
            return StageStatus.FAILED

        service = ConversationTurnSegmenter()

        try:
            segmented_transcript = service.segment(transcript)
            context.artifacts.register(segmented_transcript)
            return StageStatus.SUCCESS
        except Exception as e:
            context.warnings.append(f"Conversation turn segmentation failed: {str(e)}")
            return StageStatus.FAILED
