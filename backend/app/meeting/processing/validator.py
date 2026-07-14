"""Audio validation logic.

Verifies the integrity of meeting recordings before they enter the processing pipeline.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.meeting.artifacts.recording import MeetingRecording
from app.meeting.audio.ffmpeg_service import FFmpegService, AudioProbeResult
from app.meeting.config import meeting_config
from app.meeting.exceptions import RecordingValidationError
from app.meeting.logger import get_logger
from app.meeting.recording.storage import compute_sha256

log = get_logger("processing.validator")

# Supported formats and codecs for validation
SUPPORTED_CONTAINERS = {"webm", "wav", "ogg", "mp4"}
SUPPORTED_CODECS = {"opus", "vorbis", "aac", "pcm_s16le", "pcm_s32le", "pcm_f32le"}


@dataclass
class ValidatedRecording:
    """Internal wrapper containing the original artifact and probe details."""
    artifact: MeetingRecording
    probe: AudioProbeResult


class RecordingValidator:
    """Stateless validator for meeting recordings."""

    def __init__(self, ffmpeg: FFmpegService) -> None:
        self._ffmpeg = ffmpeg

    async def validate(self, recording: MeetingRecording) -> ValidatedRecording:
        """Run all validation checks on the recording.

        Raises:
            RecordingValidationError: On any check failure.
        """
        log.info("validation.started", recording_id=recording.id, file_path=recording.file_path)

        path = Path(recording.file_path)

        # 1 & 2: Exists and readable
        if not path.is_file():
            self._fail(recording.id, "file_exists", f"File not found: {path}")
        
        try:
            stat = path.stat()
        except OSError as exc:
            self._fail(recording.id, "file_readable", f"Cannot stat file: {exc}")
        
        # 3 & 4: Size constraints
        if stat.st_size == 0:
            self._fail(recording.id, "file_size", "File is empty (0 bytes)")
        if stat.st_size > meeting_config.MAX_RECORDING_SIZE:
            self._fail(recording.id, "file_size", f"File too large: {stat.st_size} bytes")

        # Duration constraints moved below ffprobe

        # 6: Checksum match
        try:
            actual_checksum = compute_sha256(path.read_bytes())
            if actual_checksum != recording.checksum_sha256:
                self._fail(
                    recording.id, 
                    "checksum", 
                    f"Checksum mismatch: expected {recording.checksum_sha256}, got {actual_checksum}"
                )
        except OSError as exc:
            self._fail(recording.id, "checksum_read", f"Failed to read file for checksum: {exc}")

        # 7: FFmpeg probe
        try:
            probe = await self._ffmpeg.probe(str(path))
        except Exception as exc:
            self._fail(recording.id, "ffmpeg_probe", f"Probe failed: {exc}")
            
        if probe.stream_count == 0:
            self._fail(recording.id, "audio_stream", "No streams found in file")
        if not probe.codec_name:
            self._fail(recording.id, "audio_stream", "No audio stream found in file")

        # 5: Duration constraints (moved down so `probe` is available)
        # Trust the artifact's wall-clock duration if probe is 0.0 (e.g., streaming WebM)
        actual_duration = probe.duration_seconds if probe.duration_seconds > 0 else recording.duration_seconds
        if actual_duration < meeting_config.MIN_RECORDING_DURATION:
            self._fail(recording.id, "duration", f"Recording too short: {actual_duration}s")

        # 8: Supported container
        # Note: sometimes format_name is comma separated e.g. "matroska,webm"
        formats = set(probe.format_name.split(","))
        if not formats.intersection(SUPPORTED_CONTAINERS):
            self._fail(recording.id, "container_format", f"Unsupported container(s): {probe.format_name}")

        # 9: Supported codec
        if probe.codec_name not in SUPPORTED_CODECS:
            self._fail(recording.id, "audio_codec", f"Unsupported codec: {probe.codec_name}")

        log.info("validation.completed", recording_id=recording.id, duration_ms=int(probe.duration_seconds * 1000))
        return ValidatedRecording(artifact=recording, probe=probe)

    def _fail(self, recording_id: str, check_name: str, error: str) -> None:
        """Helper to log failure and raise."""
        log.error("validation.failed", recording_id=recording_id, check_name=check_name, error=error)
        raise RecordingValidationError(f"Validation failed [{check_name}]: {error}")
