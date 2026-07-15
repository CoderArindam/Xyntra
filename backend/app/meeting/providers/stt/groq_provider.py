"""Experimental Groq STT Provider implementation (Non-intrusive)."""

import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path

from groq import AsyncGroq

from app.meeting.artifacts.recording import ProcessedAudio
from app.meeting.artifacts.transcript import RawTranscript, TranscriptSegment
from app.meeting.config import meeting_config
from app.meeting.logger import get_logger

log = get_logger("meeting.experimental.groq")


class GroqProvider:
    """Experimental STT provider using Groq Whisper API.
    
    This is intentionally NOT wired into the production provider factory.
    """

    def __init__(self) -> None:
        self._model = meeting_config.GROQ_MODEL
        if not meeting_config.GROQ_API_KEY:
            raise ValueError("MEETING_GROQ_API_KEY is not set in configuration.")
            
        self._client = AsyncGroq(
            api_key=meeting_config.GROQ_API_KEY,
            timeout=meeting_config.GROQ_TIMEOUT,
            max_retries=meeting_config.GROQ_MAX_RETRIES,
        )

    async def transcribe(self, audio: ProcessedAudio) -> RawTranscript:
        """Transcribe audio using Groq API and return a RawTranscript."""
        log.info(
            "meeting.experimental.groq.started",
            processed_audio_id=audio.id,
            file_path=audio.file_path,
        )
        
        start_time = time.monotonic()
        start_dt = datetime.now(timezone.utc)

        file_path = Path(audio.file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        try:
            log.info("meeting.experimental.groq.upload", model=self._model)
            
            with open(file_path, "rb") as f:
                # Need to use the raw groq endpoint to get verbose JSON with segments
                transcription = await self._client.audio.transcriptions.create(
                    file=(file_path.name, f.read()),
                    model=self._model,
                    response_format="verbose_json",
                    # No language specified, let Groq auto-detect
                )
                
        except Exception as exc:
            log.error("meeting.experimental.groq.failed", error=str(exc))
            raise RuntimeError(f"Groq transcription failed: {exc}") from exc

        end_time = time.monotonic()
        end_dt = datetime.now(timezone.utc)
        duration_ms = int((end_time - start_time) * 1000)

        # Parse verbose_json segments
        transcript_segments = []
        raw_segments = getattr(transcription, "segments", [])
        detected_language = getattr(transcription, "language", "unknown")
        
        for i, s in enumerate(raw_segments):
            seg = TranscriptSegment(
                meeting_id=audio.meeting_id,
                id=f"seg_{i:04d}",
                start_time=round(s.get("start", 0.0), 3),
                end_time=round(s.get("end", 0.0), 3),
                text=s.get("text", "").strip(),
                avg_logprob=float(s.get("avg_logprob", 0.0)),
                no_speech_probability=float(s.get("no_speech_prob", 0.0)),
                compression_ratio=float(s.get("compression_ratio", 0.0)),
                detected_language=detected_language,
                confidence=None,
                speaker=None,
            )
            transcript_segments.append(seg)

        # Build final artifact
        transcript = RawTranscript(
            meeting_id=audio.meeting_id,
            parent_processed_audio_id=audio.id,
            detected_language=detected_language,
            language_probability=1.0, # Groq doesn't provide this in verbose_json top level typically
            model_name=f"groq-{self._model}",
            transcription_started_at=start_dt.isoformat(),
            transcription_completed_at=end_dt.isoformat(),
            transcription_duration_ms=duration_ms,
            segments=transcript_segments,
            overall_confidence=None,
            processing_version="experimental-groq",
        )

        log.info(
            "meeting.experimental.groq.completed",
            artifact_id=transcript.id,
            duration_ms=duration_ms,
            segment_count=len(transcript_segments),
        )

        return transcript
