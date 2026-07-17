"""Deepgram speech provider — the only file that imports the Deepgram SDK.

Produces both RawTranscript and SpeakerTimeline from a single API call.
All Deepgram types are confined here; nothing downstream sees SDK objects.

SDK: deepgram-sdk 7.x — uses c.listen.v1.media.transcribe_file(request=..., **options)
Response type: ListenV1Response (Pydantic model)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from app.meeting.artifacts.recording import ProcessedAudio
from app.meeting.artifacts.speaker import (
    DiarizationProviderInfo,
    SpeakerTimeline,
    SpeakerTurn,
)
from app.meeting.artifacts.transcript import RawTranscript, TranscriptSegment, WordInfo
from app.meeting.config import meeting_config
from app.meeting.contracts.speech_provider import SpeechProvider, SpeechResult
from app.meeting.exceptions import (
    SpeechProviderAuthError,
    SpeechProviderConfigError,
    SpeechProviderError,
    SpeechProviderRateLimitError,
    SpeechProviderTimeoutError,
    SpeechProviderUnavailableError,
    SpeechProviderValidationError,
)
from app.meeting.logger import get_logger
from app.meeting.models.transcription_result import (
    TranscriptionParagraph,
    TranscriptionResult,
    TranscriptionSentence,
    TranscriptionUtterance,
    TranscriptionWord,
)
from app.meeting.providers.speech.metrics import SpeechProcessingMetrics
from app.meeting.providers.speech.retry import RetryPolicy, with_retry

log = get_logger("speech.deepgram")

_PROVIDER_NAME = "deepgram"


def _map_deepgram_error(exc: Exception) -> SpeechProviderError:
    """Convert exceptions into provider-agnostic error types."""
    msg = str(exc)

    if "401" in msg or "unauthorized" in msg.lower() or "invalid credentials" in msg.lower():
        return SpeechProviderAuthError(f"Deepgram auth failed: {msg}")
    if "429" in msg or "rate limit" in msg.lower():
        return SpeechProviderRateLimitError(f"Deepgram rate limit: {msg}")
    if "408" in msg or "timeout" in msg.lower() or "timed out" in msg.lower():
        return SpeechProviderTimeoutError(f"Deepgram timeout: {msg}")
    if "503" in msg or "502" in msg or "unavailable" in msg.lower():
        return SpeechProviderUnavailableError(f"Deepgram unavailable: {msg}")
    if "400" in msg or "invalid" in msg.lower():
        return SpeechProviderValidationError(f"Deepgram validation: {msg}")

    return SpeechProviderError(f"Deepgram error [{type(exc).__name__}]: {msg}", retryable=True)


class DeepgramSpeechProvider(SpeechProvider):
    """Cloud speech provider backed by Deepgram nova-3.

    Handles both transcription and speaker diarization in a single API call.
    Uses the deepgram-sdk 7.x API.
    """

    def __init__(self) -> None:
        if not meeting_config.DEEPGRAM_API_KEY:
            raise SpeechProviderConfigError("MEETING_DEEPGRAM_API_KEY is not set")

        from deepgram import AsyncDeepgramClient  # type: ignore

        self._client = AsyncDeepgramClient(api_key=meeting_config.DEEPGRAM_API_KEY)
        self._model = meeting_config.DEEPGRAM_MODEL
        self._retry_policy = RetryPolicy(
            max_retries=meeting_config.DEEPGRAM_MAX_RETRIES,
            base_delay=meeting_config.DEEPGRAM_BASE_DELAY,
            max_delay=meeting_config.DEEPGRAM_MAX_DELAY,
        )

    # ------------------------------------------------------------------ #
    # SpeechProvider contract                                              #
    # ------------------------------------------------------------------ #

    async def process(self, audio: ProcessedAudio) -> SpeechResult:
        request_id = str(uuid.uuid4())
        metrics = SpeechProcessingMetrics(
            request_id=request_id,
            meeting_id=audio.meeting_id,
            provider=_PROVIDER_NAME,
            model=self._model,
            audio_duration_seconds=audio.duration_seconds,
        )

        log.info(
            "speech.deepgram.started",
            request_id=request_id,
            meeting_id=audio.meeting_id,
            audio_duration_seconds=audio.duration_seconds,
            file_path=audio.file_path,
            model=self._model,
        )

        start_dt = datetime.now(timezone.utc).isoformat()

        try:
            result, retry_count = await with_retry(
                lambda: self._call_deepgram(audio, metrics),
                self._retry_policy,
                context=f"deepgram/meeting={audio.meeting_id}",
            )
            metrics.retry_count = retry_count
            metrics.mark_complete(success=True)

            log.info("speech.deepgram.completed", **metrics.to_dict())

            end_dt = datetime.now(timezone.utc).isoformat()
            return self._to_speech_result(result, audio, start_dt, end_dt, metrics)

        except SpeechProviderError as exc:
            metrics.failure_reason = str(exc)
            metrics.error_type = type(exc).__name__
            metrics.mark_complete(success=False)
            log.error("speech.deepgram.failed", **metrics.to_dict())
            raise
        except Exception as exc:
            mapped = _map_deepgram_error(exc)
            metrics.failure_reason = str(mapped)
            metrics.error_type = type(mapped).__name__
            metrics.mark_complete(success=False)
            log.error("speech.deepgram.failed", **metrics.to_dict())
            raise mapped from exc

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    async def _call_deepgram(
        self, audio: ProcessedAudio, metrics: SpeechProcessingMetrics
    ) -> TranscriptionResult:
        audio_bytes = self._read_audio(audio.file_path)

        # Phase 0X: Deepgram input verification
        try:
            session_id = audio.meeting_id
            out_dir = Path(meeting_config.PROCESSING_OUTPUT_DIR) / session_id
            out_dir.mkdir(parents=True, exist_ok=True)

            dg_wav = out_dir / "deepgram_input.wav"
            dg_webm = out_dir / "deepgram_input.webm"

            # Save the exact file sent to Deepgram if not present
            if not dg_wav.exists() and audio.file_path.endswith(".wav"):
                dg_wav.write_bytes(audio_bytes)
            
            # Look for recorded.webm in the same session dir or recording storage
            recorded_webm = out_dir / "recorded.webm"
            if recorded_webm.exists() and not dg_webm.exists():
                dg_webm.write_bytes(recorded_webm.read_bytes())

            log.info("speech.deepgram.input_verified", session_id=session_id, wav_exists=dg_wav.exists(), webm_exists=dg_webm.exists())
        except Exception as exc:
            log.warning("speech.deepgram.input_verification_warning", error=str(exc))

        # Build kwargs for transcribe_file (SDK v7 flat-kwargs style)
        transcribe_kwargs = dict(
            request=audio_bytes,
            model=self._model,
            smart_format=True,
            punctuate=True,
            diarize=True,
            utterances=True,
            paragraphs=True,
            filler_words=True,
            numerals=True,
            detect_language=True,
        )
        if meeting_config.DEEPGRAM_LANGUAGE:
            transcribe_kwargs["language"] = meeting_config.DEEPGRAM_LANGUAGE

        metrics.mark_provider_start()
        try:
            response = await self._client.listen.v1.media.transcribe_file(
                **transcribe_kwargs,
            )
        except Exception as exc:
            raise _map_deepgram_error(exc) from exc
        finally:
            metrics.mark_provider_end()

        return self._normalize_response(response, metrics)


    def _read_audio(self, file_path: str) -> bytes:
        path = Path(file_path)
        if not path.exists():
            raise SpeechProviderValidationError(f"Audio file not found: {file_path}")
        return path.read_bytes()

    def _normalize_response(
        self,
        response: object,
        metrics: SpeechProcessingMetrics,
    ) -> TranscriptionResult:
        """Convert ListenV1Response Pydantic model into TranscriptionResult."""
        try:
            # response is a ListenV1Response Pydantic model
            metadata = response.metadata  # type: ignore
            results = response.results    # type: ignore

            if results is None or not results.channels:
                raise SpeechProviderValidationError("Deepgram response has no channels")

            channel = results.channels[0]
            alternative = channel.alternatives[0]

            transcript_text: str = alternative.transcript or ""
            confidence: Optional[float] = alternative.confidence
            duration: float = float(metadata.duration or 0.0)

            # Language — deepgram v7 puts detected_language on the channel
            detected_language: str = channel.detected_language or "en"

            # Words from utterances (have speaker field)
            words = self._extract_words_from_alternative(alternative)

            # Utterances
            raw_utterances = results.utterances or []
            utterances = self._extract_utterances(raw_utterances)

            # Paragraphs
            paragraphs = self._extract_paragraphs(alternative.paragraphs)

            # Speaker summary
            speaker_labels = sorted({u.speaker for u in utterances if u.speaker})
            speaker_count = len(speaker_labels)

            metrics.detected_language = detected_language
            metrics.word_count = len(words)
            metrics.speaker_count = speaker_count
            metrics.confidence = confidence
            metrics.transcript_duration_seconds = duration

            return TranscriptionResult(
                transcript=transcript_text,
                language=detected_language,
                duration=duration,
                provider=_PROVIDER_NAME,
                model=self._model,
                confidence=confidence,
                utterances=utterances,
                paragraphs=paragraphs,
                words=words,
                speakers=speaker_labels,
                speaker_count=speaker_count,
                raw_metadata={
                    "request_id": metadata.request_id,
                    "sha256": metadata.sha256,
                },
            )
        except SpeechProviderError:
            raise
        except Exception as exc:
            raise SpeechProviderValidationError(
                f"Failed to parse Deepgram response: {exc}"
            ) from exc

    def _extract_words_from_alternative(self, alternative: object) -> List[TranscriptionWord]:
        """Extract words from channel alternative (no speaker field at word level here)."""
        raw_words = getattr(alternative, "words", None) or []
        return [
            TranscriptionWord(
                text=getattr(w, "word", ""),
                start=round(float(getattr(w, "start", 0.0)), 3),
                end=round(float(getattr(w, "end", 0.0)), 3),
                confidence=getattr(w, "confidence", None),
            )
            for w in raw_words
        ]

    def _extract_words_from_utterance(self, utterance_words: list) -> List[TranscriptionWord]:
        """Extract words from utterance (have speaker + speaker_confidence)."""
        return [
            TranscriptionWord(
                text=getattr(w, "word", ""),
                start=round(float(getattr(w, "start", 0.0)), 3),
                end=round(float(getattr(w, "end", 0.0)), 3),
                confidence=getattr(w, "confidence", None),
                speaker=_fmt_speaker(getattr(w, "speaker", None)),
                speaker_confidence=getattr(w, "speaker_confidence", None),
                punctuated_word=getattr(w, "punctuated_word", None),
            )
            for w in (utterance_words or [])
        ]

    def _extract_utterances(self, raw_utterances: list) -> List[TranscriptionUtterance]:
        utterances = []
        for u in raw_utterances:
            speaker = _fmt_speaker(getattr(u, "speaker", None))
            words = self._extract_words_from_utterance(getattr(u, "words", None) or [])
            utterances.append(
                TranscriptionUtterance(
                    speaker=speaker,
                    start=round(float(getattr(u, "start", 0.0)), 3),
                    end=round(float(getattr(u, "end", 0.0)), 3),
                    text=getattr(u, "transcript", ""),
                    confidence=getattr(u, "confidence", None),
                    words=words,
                )
            )
        return utterances

    def _extract_paragraphs(self, paragraphs_container: Optional[object]) -> List[TranscriptionParagraph]:
        if not paragraphs_container:
            return []
        raw_paras = getattr(paragraphs_container, "paragraphs", None) or []
        result = []
        for p in raw_paras:
            sentences = [
                TranscriptionSentence(
                    text=getattr(s, "text", ""),
                    start=round(float(getattr(s, "start", 0.0)), 3),
                    end=round(float(getattr(s, "end", 0.0)), 3),
                )
                for s in (getattr(p, "sentences", None) or [])
            ]
            # Reconstruct paragraph text from sentences if not available
            para_text = " ".join(s.text for s in sentences)
            result.append(
                TranscriptionParagraph(
                    speaker=_fmt_speaker(getattr(p, "speaker", None)),
                    start=round(float(getattr(p, "start", 0.0)), 3),
                    end=round(float(getattr(p, "end", 0.0)), 3),
                    text=para_text,
                    sentences=sentences,
                )
            )
        return result

    # ------------------------------------------------------------------ #
    # Artifact conversion                                                  #
    # ------------------------------------------------------------------ #

    def _to_speech_result(
        self,
        result: TranscriptionResult,
        audio: ProcessedAudio,
        start_dt: str,
        end_dt: str,
        metrics: SpeechProcessingMetrics,
    ) -> SpeechResult:
        duration_ms = metrics.total_duration_ms or 0
        transcript = self._build_raw_transcript(result, audio, start_dt, end_dt, duration_ms)
        timeline = self._build_speaker_timeline(result, audio, start_dt, end_dt, duration_ms)
        return SpeechResult(transcript=transcript, timeline=timeline)

    def _build_raw_transcript(
        self,
        result: TranscriptionResult,
        audio: ProcessedAudio,
        start_dt: str,
        end_dt: str,
        duration_ms: int,
    ) -> RawTranscript:
        segments: List[TranscriptSegment] = []

        if result.utterances:
            for i, u in enumerate(result.utterances):
                word_infos = [
                    WordInfo(
                        meeting_id=audio.meeting_id,
                        word=w.text,
                        start=w.start,
                        end=w.end,
                        confidence=w.confidence,
                        speaker=w.speaker,
                        speaker_confidence=w.speaker_confidence,
                        punctuated_word=w.punctuated_word,
                    )
                    for w in u.words
                ]
                segments.append(
                    TranscriptSegment(
                        meeting_id=audio.meeting_id,
                        id=f"seg_{i:04d}",
                        start_time=u.start,
                        end_time=u.end,
                        text=u.text,
                        confidence=u.confidence,
                        speaker=u.speaker,
                        detected_language=result.language,
                        words=word_infos,
                    )
                )
        elif result.paragraphs:
            for i, p in enumerate(result.paragraphs):
                segments.append(
                    TranscriptSegment(
                        meeting_id=audio.meeting_id,
                        id=f"seg_{i:04d}",
                        start_time=p.start,
                        end_time=p.end,
                        text=p.text,
                        speaker=p.speaker,
                        detected_language=result.language,
                    )
                )
        else:
            segments.append(
                TranscriptSegment(
                    meeting_id=audio.meeting_id,
                    id="seg_0000",
                    start_time=0.0,
                    end_time=result.duration,
                    text=result.transcript,
                    confidence=result.confidence,
                    detected_language=result.language,
                )
            )

        return RawTranscript(
            meeting_id=audio.meeting_id,
            parent_processed_audio_id=audio.id,
            detected_language=result.language,
            language_probability=result.language_confidence or 1.0,
            model_name=f"{_PROVIDER_NAME}-{result.model}",
            transcription_started_at=start_dt,
            transcription_completed_at=end_dt,
            transcription_duration_ms=duration_ms,
            segments=segments,
            overall_confidence=result.confidence,
            processing_version="2.0.0",
        )

    def _build_speaker_timeline(
        self,
        result: TranscriptionResult,
        audio: ProcessedAudio,
        start_dt: str,
        end_dt: str,
        duration_ms: int,
    ) -> SpeakerTimeline:
        turns: List[SpeakerTurn] = []
        total_speech = 0.0

        for u in result.utterances:
            if u.speaker is None:
                continue
            turns.append(
                SpeakerTurn(
                    speaker_label=u.speaker,
                    start_time=u.start,
                    end_time=u.end,
                    diarization_confidence=u.confidence or 1.0,
                )
            )
            total_speech += u.end - u.start

        return SpeakerTimeline(
            meeting_id=audio.meeting_id,
            parent_processed_audio_id=audio.id,
            provider=DiarizationProviderInfo(
                provider_name=_PROVIDER_NAME,
                provider_version=result.model,
                model_name=f"{_PROVIDER_NAME}/{result.model}",
            ),
            speaker_count=result.speaker_count,
            total_speech_duration_seconds=round(total_speech, 3),
            turns=turns,
            diarization_started_at=start_dt,
            diarization_completed_at=end_dt,
            diarization_duration_ms=duration_ms,
            processing_version=meeting_config.DIARIZATION_PROCESSING_VERSION,
        )


def _fmt_speaker(speaker_val: Optional[int]) -> Optional[str]:
    """Convert Deepgram integer speaker index to 'SPEAKER_00' format."""
    if speaker_val is None:
        return None
    return f"SPEAKER_{int(speaker_val):02d}"
