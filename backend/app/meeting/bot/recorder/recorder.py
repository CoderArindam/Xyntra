"""MeetingRecorder — browser tab audio capture using injected MediaRecorder.

Captures all meeting participant audio via a JavaScript MediaRecorder injected
into the Playwright page. Audio chunks are streamed back to Python via
page.expose_function. On stop(), the recording is persisted and returned
as a MeetingRecording artifact.
"""

from __future__ import annotations

import asyncio
import base64
import os
import tempfile
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict

from app.meeting.artifacts.recording import MeetingRecording
from app.meeting.bot.recorder.capture_script import CAPTURE_SCRIPT
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
    """Single-owner component for meeting audio capture lifecycle."""

    def __init__(self, storage: RecordingStorage) -> None:
        self._storage = storage
        self._state = RecorderState.IDLE
        self._page: Any = None
        self._session_id: str | None = None
        self._meeting_id: str | None = None

        # WebM Buffer management
        self._buffer = bytearray()
        self._temp_files: list[str] = []
        self._buffer_lock = asyncio.Lock()

        # Timing
        self._start_time: float | None = None
        self._end_time: float | None = None
        self._start_dt: datetime | None = None
        self._end_dt: datetime | None = None

        # Result
        self._mime_type: str = "audio/webm;codecs=opus"
        self._artifact: MeetingRecording | None = None

        self._stop_event = asyncio.Event()

    @property
    def state(self) -> RecorderState:
        return self._state

    @property
    def is_recording(self) -> bool:
        return self._state == RecorderState.RECORDING

    async def initialize(self, page: Any, session_id: str, meeting_id: str | None = None) -> None:
        """Inject the capture script and register chunk callbacks.

        Must be called before start(). Failures set state to FAILED.
        """
        if self._state != RecorderState.IDLE:
            return

        self._state = RecorderState.INITIALIZING
        self._page = page
        self._session_id = session_id
        self._meeting_id = meeting_id or session_id

        log.info("recording.initializing", session_id=session_id)

        try:
            # Register chunk callback BEFORE injecting script
            await page.expose_function("_kaioRecordingChunk", self._on_chunk)

            # Inject the capture script
            await page.evaluate(CAPTURE_SCRIPT)

            # Verify installation
            status = await page.evaluate("window._kaioRecordingStatus ? window._kaioRecordingStatus() : 'not_installed'")
            if status == "not_installed":
                raise RecordingInitError("Audio capture script failed to install in page context")

            self._state = RecorderState.READY
            log.info("recording.initialized", session_id=session_id, page_status=status)

        except RecordingInitError:
            self._state = RecorderState.FAILED
            raise
        except Exception as exc:
            self._state = RecorderState.FAILED
            raise RecordingInitError(f"Recorder initialization failed: {exc}") from exc

    async def start(self) -> None:
        """Signal the injected JS to begin recording."""
        if self._state != RecorderState.READY:
            log.warning(
                "recording.start.skipped",
                session_id=self._session_id,
                state=self._state.value,
            )
            return

        try:
            result = await self._page.evaluate(
                f"window._kaioStartRecording('{self._mime_type}', 1000)"
            )
            if not result.get("ok"):
                error = result.get("error", "unknown")
                raise RecordingInitError(f"JS recorder start failed: {error}")

            actual_mime = result.get("mimeType", self._mime_type)
            self._mime_type = actual_mime

            self._start_time = time.monotonic()
            self._start_dt = datetime.now(timezone.utc)
            self._state = RecorderState.RECORDING

            log.info(
                "recording.started",
                session_id=self._session_id,
                mime_type=actual_mime,
                display_surface=result.get("displaySurface"),
                logical_surface=result.get("logicalSurface"),
                cursor=result.get("cursor"),
                audio_tracks=len(result.get("audioTracks") or []),
                video_tracks=len(result.get("videoTracks") or []),
            )

        except RecordingInitError:
            self._state = RecorderState.FAILED
            raise
        except Exception as exc:
            self._state = RecorderState.FAILED
            log.error("recording.start.failed", session_id=self._session_id, error=str(exc))
            raise RecordingInitError(f"Failed to start recording: {exc}") from exc

    async def stop(self) -> MeetingRecording | None:
        """Stop the recording, persist the audio, decode, run phase 0X verification, and return artifact."""
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
            # Signal JS to stop and flush final chunks
            result = await self._page.evaluate("window._kaioStopRecording()")
            if not result.get("ok"):
                log.warning(
                    "recording.stop.js_error",
                    session_id=self._session_id,
                    error=result.get("error"),
                )

            # Give JS a moment to deliver final callbacks
            await asyncio.sleep(0.5)

            # Assemble WebM data
            audio_data = await self._assemble_audio()
            if not audio_data:
                log.warning("recording.stop.no_data", session_id=self._session_id)
                self._state = RecorderState.FAILED
                return None

            # Persist WebM recording
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
        """Abort recording immediately. Discards all buffered data."""
        if self._state in (RecorderState.COMPLETED, RecorderState.CANCELLED):
            return

        log.info("recording.cancelled", session_id=self._session_id, state=self._state.value)
        self._state = RecorderState.CANCELLED

        try:
            await asyncio.wait_for(
                self._page.evaluate("window._kaioStopRecording()"),
                timeout=2.0,
            )
        except Exception:
            pass

        await self.cleanup()

    async def cleanup(self) -> None:
        """Idempotent cleanup. Removes temp files and clears buffers."""
        log.info("recording.cleanup.started", session_id=self._session_id)
        removed = 0

        async with self._buffer_lock:
            self._buffer.clear()

        for tmp in list(self._temp_files):
            try:
                Path(tmp).unlink(missing_ok=True)
                removed += 1
            except OSError as exc:
                log.warning("recording.cleanup.temp_delete_failed", path=tmp, error=str(exc))
        self._temp_files.clear()

        log.info(
            "recording.cleanup.completed",
            session_id=self._session_id,
            temp_files_removed=removed,
        )

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    async def _on_chunk(self, b64_data: str) -> None:
        """Playwright expose_function callback for WebM chunk."""
        try:
            chunk = base64.b64decode(b64_data)
            async with self._buffer_lock:
                self._buffer.extend(chunk)
                total = len(self._buffer)

            if total >= meeting_config.RECORDING_BUFFER_SIZE:
                await self._flush_buffer()
        except Exception as exc:
            log.warning("recording.chunk.error", session_id=self._session_id, error=str(exc))

    async def _flush_buffer(self) -> None:
        async with self._buffer_lock:
            if not self._buffer:
                return
            data = bytes(self._buffer)
            self._buffer.clear()

        try:
            fd, tmp_path = tempfile.mkstemp(suffix=".part", prefix="kaio_rec_")
            os.write(fd, data)
            os.close(fd)
            self._temp_files.append(tmp_path)
        except OSError as exc:
            raise RecordingWriteError(f"Failed to flush recording buffer: {exc}") from exc

    async def _assemble_audio(self) -> bytes:
        parts: list[bytes] = []
        for tmp in self._temp_files:
            try:
                parts.append(Path(tmp).read_bytes())
            except OSError as exc:
                log.warning("recording.assemble.read_failed", path=tmp, error=str(exc))

        async with self._buffer_lock:
            if self._buffer:
                parts.append(bytes(self._buffer))
                self._buffer.clear()

        return b"".join(parts)

    async def _persist(self, audio_data: bytes) -> MeetingRecording:
        fmt = self._mime_type.split("/")[-1].split(";")[0]
        codec = "opus" if "opus" in self._mime_type else "unknown"
        checksum = compute_sha256(audio_data)

        local_path, storage_uri = await self._storage.save(
            self._session_id, audio_data, fmt
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
            format=fmt,
            sample_rate=meeting_config.RECORDING_SAMPLE_RATE,
            channel_count=2,
            codec=codec,
            mime_type=self._mime_type,
            file_size_bytes=len(audio_data),
            checksum_sha256=checksum,
            recording_start_time=self._start_dt.isoformat() if self._start_dt else "",
            recording_end_time=self._end_dt.isoformat() if self._end_dt else "",
            recording_status="completed",
        )

