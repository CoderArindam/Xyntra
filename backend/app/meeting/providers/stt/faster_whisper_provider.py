"""Faster-Whisper STT Provider implementation."""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Optional

from faster_whisper import WhisperModel

from app.meeting.artifacts.recording import ProcessedAudio
from app.meeting.artifacts.transcript import RawTranscript, TranscriptSegment
from app.meeting.config import meeting_config
from app.meeting.contracts.speech_to_text import SpeechToTextProvider
from app.meeting.exceptions import SpeechToTextError
from app.meeting.logger import get_logger

log = get_logger("meeting.stt.faster_whisper")


class FasterWhisperProvider(SpeechToTextProvider):
    """Local STT provider using faster-whisper."""

    def __init__(self) -> None:
        self._model_name = meeting_config.WHISPER_MODEL
        self._device = meeting_config.WHISPER_DEVICE
        self._compute_type = meeting_config.WHISPER_COMPUTE_TYPE
        self._model: Optional[WhisperModel] = None

    def _get_model(self) -> WhisperModel:
        """Lazy load the Whisper model."""
        if self._model is None:
            try:
                log.info(
                    "transcription.provider.loading",
                    model=self._model_name,
                    device=self._device,
                    compute_type=self._compute_type,
                )
                self._model = WhisperModel(
                    self._model_name,
                    device=self._device,
                    compute_type=self._compute_type,
                )
                log.info("transcription.provider.loaded", model=self._model_name)
            except Exception as exc:
                log.error("transcription.provider.load_error", error=str(exc))
                raise SpeechToTextError(f"Failed to load Whisper model: {exc}") from exc
        return self._model

    def _transcribe_sync(self, audio_path: str) -> tuple[Any, Any]:
        """Synchronous wrapper for transcribe to run in thread pool."""
        model = self._get_model()
        try:
            segments, info = model.transcribe(
                audio_path,
                beam_size=meeting_config.WHISPER_BEAM_SIZE,
                language=meeting_config.WHISPER_LANGUAGE if meeting_config.WHISPER_LANGUAGE else None,
                vad_filter=meeting_config.WHISPER_ENABLE_VAD,
            )
            # Exhaust the generator to force computation in the thread pool
            segments_list = list(segments)
            return segments_list, info
        except Exception as exc:
            raise SpeechToTextError(f"Whisper transcription failed: {exc}") from exc

    async def transcribe(self, audio: ProcessedAudio) -> RawTranscript:
        """Transcribe audio using faster-whisper."""
        log.info(
            "transcription.started",
            processed_audio_id=audio.id,
            file_path=audio.file_path,
        )
        
        start_time = time.monotonic()
        start_dt = datetime.now(timezone.utc)

        # Run CPU-bound inference in a separate thread
        try:
            segments_data, info = await asyncio.to_thread(
                self._transcribe_sync, audio.file_path
            )
        except Exception as exc:
            log.error("transcription.failed", processed_audio_id=audio.id, error=str(exc))
            if isinstance(exc, SpeechToTextError):
                raise
            raise SpeechToTextError(f"Transcription failed: {exc}") from exc

        end_time = time.monotonic()
        end_dt = datetime.now(timezone.utc)
        duration_ms = int((end_time - start_time) * 1000)

        # Build segments
        transcript_segments = []
        for i, s in enumerate(segments_data):
            seg = TranscriptSegment(
                meeting_id=audio.meeting_id,
                id=f"seg_{i:04d}",
                start_time=round(s.start, 3),
                end_time=round(s.end, 3),
                text=s.text.strip(),
                avg_logprob=float(s.avg_logprob),
                no_speech_probability=float(s.no_speech_prob),
                compression_ratio=float(s.compression_ratio),
                detected_language=info.language,
                confidence=None, # Intentional per requirements
                speaker=None,
            )
            transcript_segments.append(seg)

        # Build final artifact
        transcript = RawTranscript(
            meeting_id=audio.meeting_id,
            parent_processed_audio_id=audio.id,
            detected_language=info.language,
            language_probability=float(info.language_probability),
            model_name=f"faster-whisper-{self._model_name}",
            transcription_started_at=start_dt.isoformat(),
            transcription_completed_at=end_dt.isoformat(),
            transcription_duration_ms=duration_ms,
            segments=transcript_segments,
            overall_confidence=None,
            processing_version="1.0.0",
        )

        log.info(
            "transcription.completed",
            processed_audio_id=audio.id,
            artifact_id=transcript.id,
            duration_ms=duration_ms,
            detected_language=info.language,
            segment_count=len(transcript_segments),
        )

        return transcript
