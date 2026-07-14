"""FFmpeg service for audio operations.

This is the ONLY location where FFmpeg is invoked. No other module should
execute FFmpeg commands directly.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from app.meeting.config import meeting_config
from app.meeting.exceptions import AudioProcessingError
from app.meeting.logger import get_logger

log = get_logger("audio.ffmpeg")


@dataclass
class AudioProbeResult:
    stream_count: int
    duration_seconds: float
    format_name: str
    bitrate: int
    # First audio stream details
    codec_name: str = ""
    sample_rate: int = 0
    channels: int = 0


class FFmpegService:
    """Isolated FFmpeg wrapper."""

    def __init__(
        self,
        ffmpeg_path: str = meeting_config.FFMPEG_PATH,
        ffprobe_path: str = meeting_config.FFPROBE_PATH,
    ) -> None:
        self._ffmpeg = ffmpeg_path
        self._ffprobe = ffprobe_path

    async def probe(self, file_path: str) -> AudioProbeResult:
        """Run ffprobe to get container and stream metadata."""
        cmd = [
            self._ffprobe,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path,
        ]

        log.debug("processing.ffmpeg.probe.started", file_path=file_path)
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                raise AudioProcessingError(
                    f"ffprobe failed (code {proc.returncode}): {stderr.decode(errors='ignore')}"
                )

            data = json.loads(stdout)
            fmt = data.get("format", {})
            streams = data.get("streams", [])
            audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

            if not audio_streams:
                return AudioProbeResult(
                    stream_count=len(streams),
                    duration_seconds=float(fmt.get("duration", 0)),
                    format_name=fmt.get("format_name", ""),
                    bitrate=int(fmt.get("bit_rate", 0) or 0),
                )

            a_stream = audio_streams[0]
            return AudioProbeResult(
                stream_count=len(streams),
                duration_seconds=float(fmt.get("duration", 0)),
                format_name=fmt.get("format_name", ""),
                bitrate=int(fmt.get("bit_rate", 0) or 0),
                codec_name=a_stream.get("codec_name", ""),
                sample_rate=int(a_stream.get("sample_rate", 0) or 0),
                channels=int(a_stream.get("channels", 0) or 0),
            )

        except Exception as exc:
            if isinstance(exc, AudioProcessingError):
                raise
            raise AudioProcessingError(f"ffprobe execution failed: {exc}") from exc

    async def normalize(
        self,
        input_path: str,
        output_path: str,
        sample_rate: int,
        channels: int,
        format_name: str,
        codec: str = "pcm_s16le",
        enable_normalization: bool = True,
    ) -> None:
        """Convert, resample, mixdown, and optionally normalize audio."""
        cmd = [
            self._ffmpeg,
            "-y",  # Overwrite output
            "-i", input_path,
            "-vn",  # Drop video
            "-acodec", codec,
            "-ar", str(sample_rate),
            "-ac", str(channels),
            "-f", format_name,
        ]

        if enable_normalization:
            # Basic volume normalization (loudnorm is better but slower, loudnorm=I=-16:TP=-1.5:LRA=11)
            # We'll use a simple loudnorm filter for speech
            cmd.extend(["-af", "loudnorm=I=-16:TP=-1.5:LRA=11"])

        cmd.append(output_path)

        log.info("processing.ffmpeg.normalize.started", input_path=input_path, output_path=output_path)
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                raise AudioProcessingError(
                    f"ffmpeg failed (code {proc.returncode}): {stderr.decode(errors='ignore')}"
                )
            
            log.info("processing.ffmpeg.normalize.completed", output_path=output_path)

        except Exception as exc:
            if isinstance(exc, AudioProcessingError):
                raise
            raise AudioProcessingError(f"ffmpeg execution failed: {exc}") from exc
