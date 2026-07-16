"""Audio Preprocessing Stage."""

from typing import List, Type
from pathlib import Path
import os

from app.meeting.artifacts.base import MeetingArtifact
from app.meeting.artifacts.recording import MeetingRecording, ProcessedAudio
from app.meeting.pipeline.context import PipelineContext
from app.meeting.pipeline.stage import PipelineStage, StageStatus
from app.meeting.processing.service import AudioProcessingService
from app.meeting.audio.ffmpeg_service import FFmpegService
from app.meeting.processing.validator import RecordingValidator
from app.meeting.recording.storage import LocalRecordingStorage
from app.meeting.config import meeting_config

class AudioPreprocessingStage(PipelineStage):
    """Processes raw meeting recordings into normalized audio."""

    @property
    def stage_name(self) -> str:
        return "AudioPreprocessingStage"

    @property
    def execution_order(self) -> int:
        return 100

    @property
    def required_artifacts(self) -> List[Type[MeetingArtifact]]:
        return [MeetingRecording]

    @property
    def generated_artifacts(self) -> List[Type[MeetingArtifact]]:
        return [ProcessedAudio]

    @property
    def retryable(self) -> bool:
        return True

    @property
    def continue_on_failure(self) -> bool:
        return False

    async def execute(self, context: PipelineContext) -> StageStatus:
        recording = context.artifacts.get(MeetingRecording)
        if not recording:
            return StageStatus.FAILED
            
        ffmpeg = FFmpegService()
        validator = RecordingValidator(ffmpeg)
        storage = LocalRecordingStorage(root=str(meeting_config.PROCESSING_OUTPUT_DIR))
        service = AudioProcessingService(ffmpeg=ffmpeg, validator=validator, storage=storage)
        
        try:
            processed_audio = await service.process(recording)
            context.artifacts.register(processed_audio)
            return StageStatus.SUCCESS
        except Exception as e:
            context.warnings.append(f"Audio preprocessing failed: {str(e)}")
            return StageStatus.FAILED

