"""Speech Recognition Stage."""

from typing import List, Type

from app.meeting.artifacts.base import MeetingArtifact
from app.meeting.artifacts.recording import ProcessedAudio
from app.meeting.artifacts.transcript import RawTranscript
from app.meeting.pipeline.context import PipelineContext
from app.meeting.pipeline.stage import PipelineStage, StageStatus
from app.meeting.processing.transcription_service import TranscriptionService
from app.meeting.providers.stt.faster_whisper_provider import FasterWhisperProvider

class SpeechRecognitionStage(PipelineStage):
    """Transcribes processed audio into a raw transcript."""

    @property
    def stage_name(self) -> str:
        return "SpeechRecognitionStage"

    @property
    def execution_order(self) -> int:
        return 200

    @property
    def required_artifacts(self) -> List[Type[MeetingArtifact]]:
        return [ProcessedAudio]

    @property
    def generated_artifacts(self) -> List[Type[MeetingArtifact]]:
        return [RawTranscript]

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
            
        from app.meeting.config import meeting_config
        
        if meeting_config.STT_PROVIDER.lower() == "groq":
            from app.meeting.providers.stt.groq_provider import GroqProvider
            provider = GroqProvider()
        else:
            from app.meeting.providers.stt.faster_whisper_provider import FasterWhisperProvider
            provider = FasterWhisperProvider()
            
        service = TranscriptionService(provider)
        
        try:
            raw_transcript = await service.process(processed_audio)
            context.artifacts.register(raw_transcript)
            return StageStatus.SUCCESS
        except Exception as e:
            context.warnings.append(f"Transcription failed: {str(e)}")
            return StageStatus.FAILED
