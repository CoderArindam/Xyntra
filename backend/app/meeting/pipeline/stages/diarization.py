"""Speaker Diarization Stage."""

from typing import List, Type

from app.meeting.artifacts.base import MeetingArtifact
from app.meeting.artifacts.recording import ProcessedAudio
from app.meeting.artifacts.speaker import SpeakerTimeline
from app.meeting.pipeline.context import PipelineContext
from app.meeting.pipeline.stage import PipelineStage, StageStatus
from app.meeting.providers.diarization.pyannote_provider import PyannoteProvider

class SpeakerDiarizationStage(PipelineStage):
    """Identifies speaker turns and creates a timeline."""

    @property
    def stage_name(self) -> str:
        return "SpeakerDiarizationStage"

    @property
    def execution_order(self) -> int:
        return 400

    @property
    def required_artifacts(self) -> List[Type[MeetingArtifact]]:
        return [ProcessedAudio]

    @property
    def generated_artifacts(self) -> List[Type[MeetingArtifact]]:
        return [SpeakerTimeline]

    @property
    def retryable(self) -> bool:
        return True

    @property
    def continue_on_failure(self) -> bool:
        return False

    async def execute(self, context: PipelineContext) -> StageStatus:
        processed_audio = context.artifacts.get(ProcessedAudio)
        if not processed_audio:
            return StageStatus.FAILED
            
        provider = PyannoteProvider()
        
        try:
            timeline = await provider.diarize(processed_audio)
            context.artifacts.register(timeline)
            return StageStatus.SUCCESS
        except Exception as e:
            context.warnings.append(f"Diarization failed: {str(e)}")
            return StageStatus.FAILED
