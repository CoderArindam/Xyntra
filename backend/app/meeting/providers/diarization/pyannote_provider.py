"""Pyannote speaker diarization provider.

This is the only file in the entire codebase that imports pyannote.
All other modules depend only on SpeakerDiarizationProvider (the abstract
contract) and the SpeakerTimeline artifact.

To swap to NeMo, AssemblyAI, or any other provider:
  1. Create providers/diarization/<name>_provider.py
  2. Implement SpeakerDiarizationProvider
  3. Update config DIARIZATION_PROVIDER
  4. Nothing else changes.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Optional

from app.meeting.artifacts.recording import ProcessedAudio
from app.meeting.artifacts.speaker import (
    DiarizationProviderInfo,
    SpeakerTimeline,
    SpeakerTurn,
)
from app.meeting.config import meeting_config
from app.meeting.contracts.speaker_diarization import SpeakerDiarizationProvider
from app.meeting.exceptions import DiarizationError
from app.meeting.logger import get_logger

log = get_logger("diarization.pyannote")

_PROVIDER_NAME = "pyannote"
_PROVIDER_VERSION = "3.1.0"


class PyannoteProvider(SpeakerDiarizationProvider):
    """Speaker diarization using pyannote.audio.

    Lazy-loads the pipeline on first call.  Inference runs in a thread pool
    so the async event loop is never blocked.

    Requires:
        pip install pyannote.audio
        MEETING_DIARIZATION_PYANNOTE_AUTH_TOKEN set in environment/.env
    """

    def __init__(self) -> None:
        self._model_name = meeting_config.DIARIZATION_PYANNOTE_MODEL
        self._auth_token = meeting_config.DIARIZATION_PYANNOTE_AUTH_TOKEN
        self._min_speakers = meeting_config.DIARIZATION_MIN_SPEAKERS
        self._max_speakers = meeting_config.DIARIZATION_MAX_SPEAKERS
        self._pipeline = None  # lazy-loaded

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    def _get_pipeline(self):
        """Lazy-load the pyannote pipeline (model download happens once)."""
        if self._pipeline is not None:
            return self._pipeline

        try:
            from pyannote.audio import Pipeline  # type: ignore
        except ImportError as exc:
            raise DiarizationError(
                "pyannote.audio is not installed. "
                "Run: pip install pyannote.audio"
            ) from exc

        if not self._auth_token:
            raise DiarizationError(
                "MEETING_DIARIZATION_PYANNOTE_AUTH_TOKEN is not set. "
                "Obtain a token from https://hf.co/pyannote/speaker-diarization-3.1"
            )

        log.info(
            "diarization.provider.loading",
            model=self._model_name,
        )
        try:
            self._pipeline = Pipeline.from_pretrained(
                self._model_name,
                token=self._auth_token,
            )
            log.info("diarization.provider.loaded", model=self._model_name)
        except Exception as exc:
            raise DiarizationError(
                f"Failed to load pyannote pipeline '{self._model_name}': {exc}"
            ) from exc

        return self._pipeline

    def _diarize_sync(self, audio_path: str) -> list:
        """Synchronous diarization — runs in thread pool.

        Audio is pre-loaded via torchaudio and passed as a waveform dict to
        avoid torchcodec (which requires FFmpeg DLLs that may be unavailable
        on Windows). torchaudio falls back to soundfile for WAV files.
        """
        import numpy as np
        import scipy.io.wavfile  # type: ignore
        import torch  # type: ignore

        pipeline = self._get_pipeline()

        # Use scipy to load WAV — avoids torchaudio 2.11+ which routes through
        # torchcodec by default and requires FFmpeg DLLs on Windows.
        # scipy.io.wavfile is a dependency of pyannote itself (via scipy) so
        # it is always available.
        sr, data = scipy.io.wavfile.read(audio_path)

        # Normalise to float32 in [-1, 1]
        if data.dtype == np.int16:
            waveform = torch.from_numpy(data.astype(np.float32)) / 32768.0
        elif data.dtype == np.int32:
            waveform = torch.from_numpy(data.astype(np.float32)) / 2147483648.0
        else:
            waveform = torch.from_numpy(data.astype(np.float32))

        # Ensure shape is (channels, samples)
        if waveform.ndim == 1:
            waveform = waveform.unsqueeze(0)
        elif waveform.ndim == 2:
            waveform = waveform.T  # (samples, channels) → (channels, samples)

        # Mono-mix
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)

        audio_input = {"waveform": waveform, "sample_rate": sr}

        try:
            raw_output = pipeline(
                audio_input,
                min_speakers=self._min_speakers,
                max_speakers=self._max_speakers,
            )

            # pyannote 3.x → returns Annotation directly (has itertracks)
            # pyannote 4.x → returns DiarizeOutput with .speaker_diarization attribute
            if hasattr(raw_output, "itertracks"):
                annotation = raw_output
            elif hasattr(raw_output, "speaker_diarization"):
                annotation = raw_output.speaker_diarization
            else:
                raise DiarizationError(
                    f"Unsupported pyannote output type: {type(raw_output).__name__}. "
                    "Expected Annotation (3.x) or DiarizeOutput (4.x)."
                )

            return list(annotation.itertracks(yield_label=True))
        except Exception as exc:
            raise DiarizationError(f"Pyannote diarization failed: {exc}") from exc

    # ------------------------------------------------------------------ #
    # SpeakerDiarizationProvider contract                                  #
    # ------------------------------------------------------------------ #

    async def diarize(self, audio: ProcessedAudio) -> SpeakerTimeline:
        log.info(
            "diarization.started",
            processed_audio_id=audio.id,
            meeting_id=audio.meeting_id,
            file_path=audio.file_path,
        )

        start_time = time.monotonic()
        start_dt = datetime.now(timezone.utc)

        try:
            tracks = await asyncio.to_thread(self._diarize_sync, audio.file_path)
        except DiarizationError:
            log.error(
                "diarization.failed",
                processed_audio_id=audio.id,
                meeting_id=audio.meeting_id,
            )
            raise
        except Exception as exc:
            log.error(
                "diarization.failed",
                processed_audio_id=audio.id,
                meeting_id=audio.meeting_id,
                error=str(exc),
            )
            raise DiarizationError(f"Unexpected diarization failure: {exc}") from exc

        end_dt = datetime.now(timezone.utc)
        duration_ms = int((time.monotonic() - start_time) * 1000)

        # Build SpeakerTurn list — pyannote does not expose per-turn confidence
        # in all versions, so we default to 1.0 and let future versions override.
        turns: list[SpeakerTurn] = []
        speaker_labels: set[str] = set()
        total_speech = 0.0

        for segment, _track, label in tracks:
            turn = SpeakerTurn(
                speaker_label=label,
                start_time=round(segment.start, 3),
                end_time=round(segment.end, 3),
                diarization_confidence=1.0,  # pyannote 3.x does not expose per-turn score
                embedding_id=None,
            )
            turns.append(turn)
            speaker_labels.add(label)
            total_speech += segment.end - segment.start

        provider_info = DiarizationProviderInfo(
            provider_name=_PROVIDER_NAME,
            provider_version=_PROVIDER_VERSION,
            model_name=self._model_name,
        )

        timeline = SpeakerTimeline(
            meeting_id=audio.meeting_id,
            parent_processed_audio_id=audio.id,
            provider=provider_info,
            speaker_count=len(speaker_labels),
            total_speech_duration_seconds=round(total_speech, 3),
            turns=turns,
            diarization_started_at=start_dt.isoformat(),
            diarization_completed_at=end_dt.isoformat(),
            diarization_duration_ms=duration_ms,
            processing_version=meeting_config.DIARIZATION_PROCESSING_VERSION,
        )

        log.info(
            "diarization.completed",
            processed_audio_id=audio.id,
            meeting_id=audio.meeting_id,
            artifact_id=timeline.id,
            speaker_count=timeline.speaker_count,
            turn_count=len(turns),
            duration_ms=duration_ms,
        )
        log.info(
            "meeting.artifact.generated",
            artifact_type="SpeakerTimeline",
            artifact_id=timeline.id,
            meeting_id=audio.meeting_id,
        )

        return timeline
