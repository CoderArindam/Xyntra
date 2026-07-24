"""MeetingRecorder — browser audio capture using Linux Audio Subsystem (PulseAudio/PipeWire) and FFmpeg.

Captures system/browser audio output directly via FFmpeg reading from PulseAudio/PipeWire.
On stop(), the FFmpeg process is gracefully stopped via SIGINT, and the recording is
persisted and returned as a MeetingRecording artifact.
"""

from __future__ import annotations

import asyncio
import os
import signal
import tempfile
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.meeting.artifacts.recording import MeetingRecording
from app.meeting.config import meeting_config
from app.meeting.exceptions import RecordingInitError, RecordingWriteError
from app.meeting.logger import get_logger
from app.meeting.recording.storage import RecordingStorage, compute_sha256

if TYPE_CHECKING:
    pass

log = get_logger("recording")


# ------------------------------------------------------------------ #
# Recorder State                                                       #
# ------------------------------------------------------------------ #

class RecorderState(str, Enum):
    IDLE = "idle"
    INITIALIZING = "initializing"
    READY = "ready"
    RECORDING = "recording"
    STOPPING = "stopping"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


# ------------------------------------------------------------------ #
# MeetingRecorder                                                      #
# ------------------------------------------------------------------ #

class MeetingRecorder:
    """Single-owner component for meeting audio capture lifecycle via FFmpeg."""

    def __init__(self, storage: RecordingStorage) -> None:
        self._storage = storage
        self._state = RecorderState.IDLE
        self._page: Any = None
        self._session_id: str | None = None
        self._meeting_id: str | None = None

        # FFmpeg process management
        self._process: asyncio.subprocess.Process | None = None
        self._temp_output_path: str | None = None

        # Timing
        self._start_time: float | None = None
        self._end_time: float | None = None
        self._start_dt: datetime | None = None
        self._end_dt: datetime | None = None

        # Metadata
        self._mime_type: str = "audio/webm;codecs=opus"
        self._artifact: MeetingRecording | None = None

    @property
    def state(self) -> RecorderState:
        return self._state

    @property
    def is_recording(self) -> bool:
        return self._state == RecorderState.RECORDING

    async def initialize(self, page: Any, session_id: str, meeting_id: str | None = None) -> None:
        """Prepare recorder for session.

        Must be called before start(). Maintained for signature & lifecycle compatibility.
        """
        if self._state != RecorderState.IDLE:
            return

        self._state = RecorderState.INITIALIZING
        self._page = page
        self._session_id = session_id
        self._meeting_id = meeting_id or session_id

        log.info("recording.initializing", session_id=session_id)

        try:
            self._state = RecorderState.READY
            log.info("recording.initialized", session_id=session_id)
        except Exception as exc:
            self._state = RecorderState.FAILED
            raise RecordingInitError(f"Recorder initialization failed: {exc}") from exc

    async def start(self) -> None:
        """Spawn FFmpeg process to capture browser/system audio from PulseAudio."""
        if self._state != RecorderState.READY:
            log.warning(
                "recording.start.skipped",
                session_id=self._session_id,
                state=self._state.value,
            )
            return

        try:
            fd, tmp_path = tempfile.mkstemp(suffix=".webm", prefix="kaio_rec_")
            os.close(fd)
            self._temp_output_path = tmp_path

            import sys
            pulse_source = getattr(meeting_config, "RECORDING_PULSE_SOURCE", "default")
            
            if sys.platform == "win32":
                win_device = getattr(meeting_config, "RECORDING_WIN_AUDIO_DEVICE", "")
                if win_device:
                    audio_input = ["-f", "dshow", "-i", f"audio={win_device}"]
                else:
                    audio_input = ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000"]
            else:
                audio_input = ["-f", "pulse", "-i", pulse_source]

            cmd = [
                meeting_config.FFMPEG_PATH,
                "-y",
                *audio_input,
                "-acodec", "libopus",
                "-ar", str(meeting_config.RECORDING_SAMPLE_RATE),
                "-ac", "2",
                "-b:a", "128k",
                "-f", "webm",
                self._temp_output_path,
            ]

            log.info("recording.ffmpeg.starting", session_id=self._session_id, pulse_source=pulse_source, platform=sys.platform, output=self._temp_output_path)

            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            self._start_time = time.monotonic()
            self._start_dt = datetime.now(timezone.utc)
            self._state = RecorderState.RECORDING

            log.info("recording.started", session_id=self._session_id, pid=self._process.pid)

        except Exception as exc:
            self._state = RecorderState.FAILED
            log.error("recording.start.failed", session_id=self._session_id, error=str(exc))
            raise RecordingInitError(f"Failed to start FFmpeg recording process: {exc}") from exc

    async def stop(self) -> MeetingRecording | None:
        """Stop FFmpeg process gracefully, read WebM audio, persist artifact, and return."""
        if self._state not in (RecorderState.RECORDING, RecorderState.READY):
            log.info(
                "recording.stop.skipped",
                session_id=self._session_id,
                state=self._state.value,
            )
            return None

        self._state = RecorderState.STOPPING
        self._end_time = time.monotonic()
        self._end_dt = datetime.now(timezone.utc)

        log.info("recording.stopping", session_id=self._session_id)

        try:
            if self._process and self._process.returncode is None:
                try:
                    import sys
                    if sys.platform != "win32" and hasattr(signal, "SIGINT"):
                        self._process.send_signal(signal.SIGINT)
                    else:
                        self._process.terminate()
                    await asyncio.wait_for(self._process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    log.warning("recording.ffmpeg.stop_timeout", session_id=self._session_id)
                    try:
                        self._process.terminate()
                        await asyncio.wait_for(self._process.wait(), timeout=2.0)
                    except Exception:
                        self._process.kill()
                except Exception as exc:
                    log.warning("recording.ffmpeg.stop_error", session_id=self._session_id, error=str(exc))
                    try:
                        self._process.kill()
                    except Exception:
                        pass

            if not self._temp_output_path or not Path(self._temp_output_path).exists():
                log.warning("recording.stop.no_file", session_id=self._session_id)
                self._state = RecorderState.FAILED
                return None

            audio_data = Path(self._temp_output_path).read_bytes()
            if not audio_data:
                log.warning("recording.stop.no_data", session_id=self._session_id)
                self._state = RecorderState.FAILED
                return None

            artifact = await self._persist(audio_data)
            self._artifact = artifact

            self._state = RecorderState.COMPLETED
            log.info(
                "recording.completed",
                session_id=self._session_id,
                artifact_id=artifact.id,
                duration_seconds=artifact.duration_seconds,
                file_size_bytes=artifact.file_size_bytes,
            )
            return artifact

        except Exception as exc:
            self._state = RecorderState.FAILED
            log.error("recording.stop.failed", session_id=self._session_id, error=str(exc))
            return None

    async def cancel(self) -> None:
        """Abort recording immediately. Terminate FFmpeg process and discard data."""
        if self._state in (RecorderState.COMPLETED, RecorderState.CANCELLED):
            return

        log.info("recording.cancelled", session_id=self._session_id, state=self._state.value)
        self._state = RecorderState.CANCELLED

        if self._process and self._process.returncode is None:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=2.0)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass

        await self.cleanup()

    async def cleanup(self) -> None:
        """Idempotent cleanup. Removes temporary file artifacts."""
        log.info("recording.cleanup.started", session_id=self._session_id)

        if self._temp_output_path:
            try:
                Path(self._temp_output_path).unlink(missing_ok=True)
            except OSError as exc:
                log.warning("recording.cleanup.temp_delete_failed", path=self._temp_output_path, error=str(exc))
            self._temp_output_path = None

        self._process = None
        log.info("recording.cleanup.completed", session_id=self._session_id)

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    async def _persist(self, audio_data: bytes) -> MeetingRecording:
        checksum = compute_sha256(audio_data)

        local_path, storage_uri = await self._storage.save(
            self._session_id, audio_data, "webm"
        )

        duration = (
            (self._end_time - self._start_time)
            if self._start_time and self._end_time
            else 0.0
        )

        return MeetingRecording(
            meeting_id=self._meeting_id,
            file_path=local_path,
            storage_uri=storage_uri,
            duration_seconds=round(duration, 3),
            format="webm",
            sample_rate=meeting_config.RECORDING_SAMPLE_RATE,
            channel_count=2,
            codec="opus",
            mime_type=self._mime_type,
            file_size_bytes=len(audio_data),
            checksum_sha256=checksum,
            recording_start_time=self._start_dt.isoformat() if self._start_dt else "",
            recording_end_time=self._end_dt.isoformat() if self._end_dt else "",
            recording_status="completed",
        )
