"""Unified Speech Processing Stage.

Replaces the separate SpeechRecognitionStage (Whisper) and
SpeakerDiarizationStage (Pyannote) with a single cloud-provider stage.

The active provider is determined by MEETING_SPEECH_PROVIDER config.
Produces both RawTranscript and SpeakerTimeline atomically.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import List, Type

from app.meeting.artifacts.base import MeetingArtifact
from app.meeting.artifacts.recording import ProcessedAudio
from app.meeting.artifacts.speaker import SpeakerTimeline
from app.meeting.artifacts.transcript import RawTranscript
from app.meeting.exceptions import SpeechProviderError
from app.meeting.logger import get_logger
from app.meeting.pipeline.context import PipelineContext
from app.meeting.pipeline.stage import PipelineStage, StageStatus
from app.meeting.providers.speech.factory import get_speech_provider

log = get_logger("pipeline.speech_processing")


class SpeechProcessingStage(PipelineStage):
    """Unified STT + diarization stage backed by a cloud speech provider.

    Input:  ProcessedAudio
    Output: RawTranscript + SpeakerTimeline

    Both artifacts are produced in a single provider call. Downstream stages
    (normalization → alignment → mapping) are unchanged.
    """

    @property
    def stage_name(self) -> str:
        return "SpeechProcessingStage"

    @property
    def execution_order(self) -> int:
        return 200

    @property
    def required_artifacts(self) -> List[Type[MeetingArtifact]]:
        return [ProcessedAudio]

    @property
    def generated_artifacts(self) -> List[Type[MeetingArtifact]]:
        return [RawTranscript, SpeakerTimeline]

    @property
    def retryable(self) -> bool:
        # Retry is handled inside the provider's own retry engine.
        # The orchestrator-level retry is disabled to avoid double-retry.
        return False

    @property
    def continue_on_failure(self) -> bool:
        return False

    async def execute(self, context: PipelineContext) -> StageStatus:
        audio = context.artifacts.get(ProcessedAudio)
        if not audio:
            context.warnings.append("SpeechProcessingStage: ProcessedAudio not found")
            return StageStatus.FAILED

        t0 = time.monotonic()
        start_dt = datetime.now(timezone.utc).isoformat()

        try:
            provider = get_speech_provider()
            result = await provider.process(audio)

            duration_ms = int((time.monotonic() - t0) * 1000)

            # Patch in the actual round-trip duration
            transcript = result.transcript.model_copy(
                update={
                    "transcription_started_at": start_dt,
                    "transcription_completed_at": datetime.now(timezone.utc).isoformat(),
                    "transcription_duration_ms": duration_ms,
                }
            )
            timeline = result.timeline.model_copy(
                update={
                    "diarization_started_at": start_dt,
                    "diarization_completed_at": datetime.now(timezone.utc).isoformat(),
                    "diarization_duration_ms": duration_ms,
                }
            )

            context.artifacts.register(transcript)
            context.artifacts.register(timeline)

            log.info(
                "pipeline.speech_processing.completed",
                meeting_id=audio.meeting_id,
                duration_ms=duration_ms,
                segment_count=len(transcript.segments),
                speaker_count=timeline.speaker_count,
                detected_language=transcript.detected_language,
            )

            return StageStatus.SUCCESS

        except SpeechProviderError as exc:
            log.error(
                "pipeline.speech_processing.failed",
                meeting_id=audio.meeting_id,
                error_code=exc.code,
                retryable=exc.retryable,
                error=str(exc),
            )
            context.warnings.append(f"Speech processing failed: {exc}")
            return StageStatus.FAILED

        except Exception as exc:
            log.error(
                "pipeline.speech_processing.unexpected_error",
                meeting_id=audio.meeting_id,
                error=str(exc),
            )
            context.warnings.append(f"Speech processing unexpected error: {exc}")
            return StageStatus.FAILED
