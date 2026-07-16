"""Transcript Normalization Stage."""

from typing import List, Type

from app.meeting.artifacts.base import MeetingArtifact
from app.meeting.artifacts.transcript import RawTranscript, NormalizedTranscript
from app.meeting.pipeline.context import PipelineContext
from app.meeting.pipeline.stage import PipelineStage, StageStatus
from app.meeting.normalization.service import TranscriptNormalizationService

class TranscriptNormalizationStage(PipelineStage):
    """Normalizes and cleans raw transcript segments."""

    @property
    def stage_name(self) -> str:
        return "TranscriptNormalizationStage"

    @property
    def execution_order(self) -> int:
        return 300

    @property
    def required_artifacts(self) -> List[Type[MeetingArtifact]]:
        return [RawTranscript]

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
        raw_transcript = context.artifacts.get(RawTranscript)
        if not raw_transcript:
            return StageStatus.FAILED
            
        service = TranscriptNormalizationService()
        
        try:
            normalized_transcript = await service.normalize(raw_transcript)
            context.artifacts.register(normalized_transcript)
            return StageStatus.SUCCESS
        except Exception as e:
            context.warnings.append(f"Normalization failed: {str(e)}")
            return StageStatus.FAILED
