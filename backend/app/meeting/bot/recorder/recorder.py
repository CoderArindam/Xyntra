"""MeetingRecorder — browser tab audio capture using injected MediaRecorder + Phase 0X observability.

Captures all meeting participant audio via a JavaScript MediaRecorder injected
into the Playwright page and streams raw PCM audio concurrently.
Audio chunks are streamed back to Python via page.expose_function.
On stop(), the recording is persisted, verified, decoded, analyzed, and full phase 0X debug
artifacts are generated.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

from app.meeting.artifacts.audio_debug import (
    AudioCaptureDebugArtifact,
    AudioGraphNodeInfo,
    AudioTrackMetadata,
)
from app.meeting.artifacts.recording import MeetingRecording
from app.meeting.audio.ffmpeg_service import FFmpegService
from app.meeting.audio.verification import (
    analyze_speech_activity,
    calculate_audio_metrics,
    generate_spectrogram_plot,
    generate_waveform_plot,
    write_pcm16_wav,
)
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

        # Raw PCM Buffer management (Phase 0X)
        self._raw_pcm_buffer = bytearray()
        self._raw_pcm_lock = asyncio.Lock()

        # Timing
        self._start_time: float | None = None
        self._end_time: float | None = None
        self._start_dt: datetime | None = None
        self._end_dt: datetime | None = None

        # Result
        self._mime_type: str = "audio/webm;codecs=opus"
        self._artifact: MeetingRecording | None = None
        self._js_start_meta: Dict[str, Any] = {}
        self._js_stop_meta: Dict[str, Any] = {}

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
            # Register chunk callbacks BEFORE injecting script
            await page.expose_function("_kaioRecordingChunk", self._on_chunk)
            await page.expose_function("_kaioRawPcmChunk", self._on_raw_pcm_chunk)

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
            self._js_start_meta = result

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
            self._js_stop_meta = result

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

            # -------------------------------------------------------------- #
            # Phase 0X: Observability & Audio Pipeline Verification          #
            # -------------------------------------------------------------- #
            await self._run_phase_0x_verification(artifact, audio_data)

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

        async with self._raw_pcm_lock:
            self._raw_pcm_buffer.clear()

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

    async def _on_raw_pcm_chunk(self, b64_data: str) -> None:
        """Playwright expose_function callback for raw PCM int16 chunk."""
        try:
            chunk = base64.b64decode(b64_data)
            async with self._raw_pcm_lock:
                self._raw_pcm_buffer.extend(chunk)
        except Exception as exc:
            log.warning("recording.raw_pcm_chunk.error", session_id=self._session_id, error=str(exc))

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

    # ------------------------------------------------------------------ #
    # Phase 0X Observability Pipeline Execution                            #
    # ------------------------------------------------------------------ #

    async def _run_phase_0x_verification(
        self, recording_artifact: MeetingRecording, webm_bytes: bytes
    ) -> None:
        """Generate all 14 diagnostic verification artifacts required for Phase 0X."""
        session_id = self._session_id or "unknown_session"
        out_dir = Path(meeting_config.PROCESSING_OUTPUT_DIR) / session_id
        out_dir.mkdir(parents=True, exist_ok=True)

        log.info("phase_0x.verification.started", session_id=session_id, output_dir=str(out_dir))

        try:
            # 1. Export capture_raw.wav (The most important artifact of Phase 0X)
            async with self._raw_pcm_lock:
                pcm_bytes = bytes(self._raw_pcm_buffer)
            raw_wav_path = out_dir / "capture_raw.wav"
            write_pcm16_wav(raw_wav_path, pcm_bytes, sample_rate=48000, channels=2)

            # 2. Save recorded.webm
            webm_path = out_dir / "recorded.webm"
            webm_path.write_bytes(webm_bytes)

            # 3. Decode recorded.webm -> recorded_decoded.wav
            ffmpeg = FFmpegService()
            decoded_wav_path = out_dir / "recorded_decoded.wav"
            await ffmpeg.normalize(
                input_path=str(webm_path),
                output_path=str(decoded_wav_path),
                sample_rate=48000,
                channels=2,
                format_name="wav",
                codec="pcm_s16le",
                enable_normalization=False,
            )

            # 4. Calculate channel metrics for both signals
            raw_metrics = calculate_audio_metrics(raw_wav_path)
            decoded_metrics = calculate_audio_metrics(decoded_wav_path)

            # 5. Generate Waveforms & Spectrograms
            generate_waveform_plot(raw_wav_path, out_dir / "waveform_capture.png", "Raw Audio Signal Entering MediaRecorder")
            generate_waveform_plot(decoded_wav_path, out_dir / "waveform_recorded.png", "Decoded Audio Signal from MediaRecorder")
            generate_spectrogram_plot(raw_wav_path, out_dir / "spectrogram_capture.png", "Raw Audio Spectrogram")
            generate_spectrogram_plot(decoded_wav_path, out_dir / "spectrogram_recorded.png", "Decoded Recorded Spectrogram")

            # 6. Perform speech energy activity analysis
            speech_activity = analyze_speech_activity(raw_wav_path)
            (out_dir / "speech_activity.json").write_text(json.dumps(speech_activity, indent=2), encoding="utf-8")

            # 7. Collect Timeline
            timeline_events = self._js_start_meta.get("timeline", [])
            stop_timeline = self._js_stop_meta.get("timeline", [])
            combined_timeline = timeline_events + [e for e in stop_timeline if e not in timeline_events]
            (out_dir / "audio_pipeline_timeline.json").write_text(json.dumps(combined_timeline, indent=2), encoding="utf-8")

            # 8. Produce Browser Launch Debug (if available)
            launch_debug = {
                "session_id": session_id,
                "browser_version": self._js_start_meta.get("browserVersion", "Chromium"),
                "display_surface": self._js_start_meta.get("displaySurface"),
                "logical_surface": self._js_start_meta.get("logicalSurface"),
                "cursor": self._js_start_meta.get("cursor"),
                "device_id": self._js_start_meta.get("deviceId"),
                "group_id": self._js_start_meta.get("groupId"),
            }
            (out_dir / "browser_launch_debug.json").write_text(json.dumps(launch_debug, indent=2), encoding="utf-8")

            # 9. Automated Audio Verification Report
            warnings = []
            if raw_metrics.get("rms", 0.0) < 1e-4:
                warnings.append("Raw captured PCM audio energy is near zero (silent source)")
            if decoded_metrics.get("rms", 0.0) < 1e-4:
                warnings.append("Decoded MediaRecorder output energy is near zero")
            if speech_activity.get("speech_ratio", 0.0) < 0.05:
                warnings.append("Only one active audio source or low speech energy detected")

            verification_report = {
                "session_id": session_id,
                "audio_tracks": len(self._js_start_meta.get("audioTracks") or []),
                "video_tracks": len(self._js_start_meta.get("videoTracks") or []),
                "display_surface": self._js_start_meta.get("displaySurface", "unknown"),
                "capture_duration": recording_artifact.duration_seconds,
                "raw_pcm_duration": raw_metrics.get("duration", 0.0),
                "recorded_duration": decoded_metrics.get("duration", 0.0),
                "sample_rate": 48000,
                "channels": 2,
                "raw_pcm_rms": raw_metrics.get("rms", 0.0),
                "recorded_rms": decoded_metrics.get("rms", 0.0),
                "raw_peak_amplitude": raw_metrics.get("peak_amplitude", 0.0),
                "recorded_peak_amplitude": decoded_metrics.get("peak_amplitude", 0.0),
                "mediarecorder_mime": self._mime_type,
                "warnings": warnings,
            }
            (out_dir / "audio_capture_report.json").write_text(json.dumps(verification_report, indent=2), encoding="utf-8")

            # 10. Instantiate and write AudioCaptureDebugArtifact
            audio_tracks_meta = [
                AudioTrackMetadata(
                    id=t.get("id", ""),
                    label=t.get("label", ""),
                    kind=t.get("kind", "audio"),
                    enabled=t.get("enabled", True),
                    muted=t.get("muted", False),
                    readyState=t.get("readyState", "live"),
                    settings=t.get("settings", {}),
                    constraints=t.get("constraints", {}),
                    capabilities=t.get("capabilities", {}),
                )
                for t in (self._js_start_meta.get("audioTracks") or [])
            ]
            video_tracks_meta = [
                AudioTrackMetadata(
                    id=t.get("id", ""),
                    label=t.get("label", ""),
                    kind=t.get("kind", "video"),
                    enabled=t.get("enabled", True),
                    muted=t.get("muted", False),
                    readyState=t.get("readyState", "live"),
                    settings=t.get("settings", {}),
                    constraints=t.get("constraints", {}),
                    capabilities=t.get("capabilities", {}),
                )
                for t in (self._js_start_meta.get("videoTracks") or [])
            ]
            audio_graph_meta = [
                AudioGraphNodeInfo(
                    node_type=g.get("node_type", ""),
                    number_of_inputs=g.get("number_of_inputs", 0),
                    number_of_outputs=g.get("number_of_outputs", 0),
                    channel_count=g.get("channel_count", 2),
                    channel_count_mode=g.get("channel_count_mode", "max"),
                )
                for g in (self._js_start_meta.get("audioGraph") or [])
            ]

            debug_artifact = AudioCaptureDebugArtifact(
                meeting_id=session_id,
                capture_timestamp=self._start_dt.isoformat() if self._start_dt else datetime.now(timezone.utc).isoformat(),
                browser_version=self._js_start_meta.get("browserVersion", "Chromium"),
                platform="Desktop",
                selected_mime_type=self._mime_type,
                number_of_audio_tracks=len(audio_tracks_meta),
                number_of_video_tracks=len(video_tracks_meta),
                audio_tracks=audio_tracks_meta,
                video_tracks=video_tracks_meta,
                audio_graph=audio_graph_meta,
                display_surface=self._js_start_meta.get("displaySurface"),
                logical_surface=self._js_start_meta.get("logicalSurface"),
                cursor=self._js_start_meta.get("cursor"),
                device_id=self._js_start_meta.get("deviceId"),
                group_id=self._js_start_meta.get("groupId"),
            )
            (out_dir / "audio_capture_debug.json").write_text(debug_artifact.model_dump_json(indent=2), encoding="utf-8")

            log.info("phase_0x.verification.completed", session_id=session_id, report=verification_report)

        except Exception as exc:
            log.error("phase_0x.verification.failed", session_id=session_id, error=str(exc))
