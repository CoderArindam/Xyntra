"""Audio Processing Service.

Implements the AudioProcessor contract. Transforms a MeetingRecording into
a ProcessedAudio artifact via FFmpeg normalization.
"""

from __future__ import annotations

import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from app.meeting.artifacts.recording import MeetingRecording, ProcessedAudio
from app.meeting.audio.ffmpeg_service import FFmpegService
from app.meeting.config import meeting_config
from app.meeting.contracts.audio import AudioProcessor
from app.meeting.exceptions import AudioProcessingError
from app.meeting.logger import get_logger
from app.meeting.processing.validator import RecordingValidator
from app.meeting.recording.storage import RecordingStorage, compute_sha256

log = get_logger("processing.service")


class AudioProcessingService(AudioProcessor):
    """Concrete implementation of the audio processor pipeline stage."""

    def __init__(
        self,
        ffmpeg: FFmpegService,
        validator: RecordingValidator,
        storage: RecordingStorage,
    ) -> None:
        self._ffmpeg = ffmpeg
        self._validator = validator
        self._storage = storage

    async def process(self, recording: MeetingRecording) -> ProcessedAudio:
        """Validate, normalize, persist, and produce a ProcessedAudio artifact.

        Original recording is never modified.
        """
        start_time = time.monotonic()
        start_dt = datetime.now(timezone.utc)
        log.info("processing.started", meeting_id=recording.meeting_id, recording_id=recording.id)

        # 1. Validate
        validated = await self._validator.validate(recording)

        # 2. Normalize (convert, resample, mixdown)
        fd, tmp_path = tempfile.mkstemp(suffix=f".{meeting_config.CANONICAL_FORMAT}", prefix="kaio_proc_")
        os.close(fd)
        
        try:
            await self._ffmpeg.normalize(
                input_path=validated.artifact.file_path,
                output_path=tmp_path,
                sample_rate=meeting_config.CANONICAL_SAMPLE_RATE,
                channels=meeting_config.CANONICAL_CHANNELS,
                format_name=meeting_config.CANONICAL_FORMAT,
                codec="pcm_s16le",
                enable_normalization=meeting_config.ENABLE_AUDIO_NORMALIZATION,
            )
            
            # Read processed bytes for persistence
            processed_bytes = Path(tmp_path).read_bytes()
            
            if not processed_bytes:
                raise AudioProcessingError("FFmpeg produced an empty file")
                
            # Probe the NEW canonical file to get perfect metadata (duration, etc.)
            processed_probe = await self._ffmpeg.probe(str(tmp_path))

        except Exception as exc:
            # Cleanup temp on failure
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except OSError:
                pass
            
            log.error("processing.failed", recording_id=recording.id, error=str(exc))
            raise
            
        # 3. Persist via storage abstraction
        try:
            local_path, storage_uri = await self._storage.save(
                session_id=recording.meeting_id,
                data=processed_bytes,
                fmt=meeting_config.CANONICAL_FORMAT,
            )
        finally:
            # Always clean up temp file after persistence attempt
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except OSError:
                pass

        # 4. Finalize metadata and artifact
        checksum = compute_sha256(processed_bytes)
        end_time = time.monotonic()
        end_dt = datetime.now(timezone.utc)
        duration_ms = int((end_time - start_time) * 1000)

        artifact = ProcessedAudio(
            meeting_id=recording.meeting_id,
            parent_recording_id=recording.id,
            file_path=local_path,
            storage_uri=storage_uri,
            duration_seconds=processed_probe.duration_seconds, # Perfect exact duration from the processed WAV
            format=meeting_config.CANONICAL_FORMAT,
            codec="pcm_s16le",
            sample_rate=meeting_config.CANONICAL_SAMPLE_RATE,
            channels=meeting_config.CANONICAL_CHANNELS,
            bitrate=16 * meeting_config.CANONICAL_SAMPLE_RATE * meeting_config.CANONICAL_CHANNELS,
            file_size_bytes=len(processed_bytes),
            checksum_sha256=checksum,
            processing_started_at=start_dt.isoformat(),
            processing_completed_at=end_dt.isoformat(),
            processing_duration_ms=duration_ms,
            processing_version="1.0.0",
        )

        log.info(
            "processing.completed",
            artifact_id=artifact.id,
            recording_id=recording.id,
            duration_ms=duration_ms,
        )
        
        return artifact
