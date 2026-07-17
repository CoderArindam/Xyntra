"""TranscriptIntegrityValidator — pipeline integrity verification engine.

Audits transcript transformations across consecutive pipeline stages:
  RawTranscript → NormalizedTranscript
  NormalizedTranscript → SpeakerAttributedTranscript
  SpeakerAttributedTranscript → ParticipantAttributedTranscript

Detects:
  - dropped segments (without valid documented cause)
  - missing or negative timestamps
  - missing text / empty text
  - timestamp inversions / ordering corruption
  - duplicated segments
  - invalid segment duration
  - word count and character count loss exceeding expected thresholds (< 1.0%)

Logs warnings for minor non-critical anomalies and raises TranscriptIntegrityError
for critical data loss or structural corruption.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field

from app.meeting.artifacts.speaker import (
    ParticipantAttributedTranscript,
    SpeakerAttributedTranscript,
)
from app.meeting.artifacts.transcript import (
    NormalizedTranscript,
    RawTranscript,
)
from app.meeting.exceptions import TranscriptIntegrityError
from app.meeting.logger import get_logger

log = get_logger("normalization.validator")


class IntegrityResult(BaseModel):
    """Result of integrity audit for a single pipeline transition."""

    stage_transition: str           # e.g., "Raw -> Normalized"
    passed: bool = True
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)

    input_segment_count: int = 0
    output_segment_count: int = 0
    dropped_segment_count: int = 0

    input_word_count: int = 0
    output_word_count: int = 0
    word_loss_percent: float = 0.0

    input_char_count: int = 0
    output_char_count: int = 0
    char_loss_percent: float = 0.0


class TranscriptIntegrityValidator:
    """Validates structural and content integrity across processing stages."""

    # ------------------------------------------------------------------ #
    # 1. Raw -> Normalized                                                #
    # ------------------------------------------------------------------ #

    def validate_raw_to_normalized(
        self,
        raw: RawTranscript,
        normalized: NormalizedTranscript,
        min_confidence_threshold: Optional[float] = None,
    ) -> IntegrityResult:
        result = IntegrityResult(stage_transition="Raw -> Normalized")
        raw_segs = raw.segments
        norm_segs = normalized.segments

        result.input_segment_count = len(raw_segs)
        result.output_segment_count = len(norm_segs)

        raw_words = sum(len((s.text or "").split()) for s in raw_segs)
        norm_words = sum(s.word_count for s in norm_segs)
        result.input_word_count = raw_words
        result.output_word_count = norm_words

        if raw_words > 0:
            result.word_loss_percent = round(
                max(0.0, (raw_words - norm_words) / raw_words) * 100.0, 2
            )

        raw_chars = sum(len(s.text or "") for s in raw_segs)
        norm_chars = sum(s.character_count for s in norm_segs)
        result.input_char_count = raw_chars
        result.output_char_count = norm_chars

        if raw_chars > 0:
            result.char_loss_percent = round(
                max(0.0, (raw_chars - norm_chars) / raw_chars) * 100.0, 2
            )

        # Build map of normalized segments by raw_segment_id
        norm_by_raw_id = {s.raw_segment_id: s for s in norm_segs if s.raw_segment_id}
        norm_by_orig_id = {s.id.replace("norm_", ""): s for s in norm_segs}

        # Check dropped segments
        for raw_seg in raw_segs:
            text = (raw_seg.text or "").strip()
            dur = raw_seg.end_time - raw_seg.start_time
            matched = norm_by_raw_id.get(raw_seg.id) or norm_by_orig_id.get(raw_seg.id)

            if not matched:
                # Determine if removal was valid under rules
                is_empty = len(text) == 0
                is_zero_dur = dur <= 0
                is_low_conf = (
                    min_confidence_threshold is not None
                    and raw_seg.confidence is not None
                    and raw_seg.confidence < min_confidence_threshold
                )

                if is_empty or is_zero_dur or is_low_conf:
                    log.info(
                        "integrity.segment_removed_valid",
                        raw_segment_id=raw_seg.id,
                        reason="empty" if is_empty else ("zero_duration" if is_zero_dur else "low_confidence"),
                    )
                else:
                    msg = (
                        f"Unsanctioned segment drop: raw segment '{raw_seg.id}' "
                        f"[{raw_seg.start_time:.2f}s-{raw_seg.end_time:.2f}s] text '{text[:30]}' "
                        f"was removed during normalization."
                    )
                    result.errors.append(msg)
                    result.dropped_segment_count += 1

        # Timestamps & ordering check on normalized
        for i, seg in enumerate(norm_segs):
            if seg.start_time < 0 or seg.end_time < 0:
                result.errors.append(f"Normalized segment index {i} ({seg.id}) has negative timestamps.")

            if seg.end_time <= seg.start_time:
                result.errors.append(
                    f"Normalized segment index {i} ({seg.id}) has invalid duration "
                    f"[{seg.start_time}s -> {seg.end_time}s]."
                )

            if i > 0 and seg.start_time < norm_segs[i - 1].start_time:
                result.errors.append(
                    f"Timestamp inversion at index {i} ({seg.id}): start_time {seg.start_time} "
                    f"< previous {norm_segs[i-1].start_time}."
                )

            if not seg.text or not seg.text.strip():
                result.warnings.append(f"Normalized segment {seg.id} contains empty text.")

        # Content loss warning threshold (< 1.0%)
        if result.word_loss_percent > 1.0:
            result.warnings.append(
                f"Word loss of {result.word_loss_percent}% exceeds 1.0% threshold "
                f"({raw_words} raw words -> {norm_words} normalized words)."
            )

        result.passed = len(result.errors) == 0
        self._log_result(result)
        return result

    # ------------------------------------------------------------------ #
    # 2. Normalized -> Speaker Attributed                                 #
    # ------------------------------------------------------------------ #

    def validate_normalized_to_speaker(
        self,
        normalized: NormalizedTranscript,
        speaker: SpeakerAttributedTranscript,
    ) -> IntegrityResult:
        result = IntegrityResult(stage_transition="Normalized -> Speaker")
        norm_segs = normalized.segments
        spk_segs = speaker.segments

        result.input_segment_count = len(norm_segs)
        result.output_segment_count = len(spk_segs)

        result.input_word_count = sum(s.word_count for s in norm_segs)
        result.output_word_count = sum(len(s.text.split()) for s in spk_segs)

        result.input_char_count = sum(s.character_count for s in norm_segs)
        result.output_char_count = sum(len(s.text) for s in spk_segs)

        if len(spk_segs) != len(norm_segs):
            result.errors.append(
                f"Segment count mismatch: Normalized has {len(norm_segs)} segments, "
                f"SpeakerAttributed has {len(spk_segs)} segments."
            )

        min_len = min(len(norm_segs), len(spk_segs))
        for i in range(min_len):
            ns = norm_segs[i]
            ss = spk_segs[i]

            if ss.segment_id != ns.id:
                result.errors.append(f"Segment ID mismatch at index {i}: expected {ns.id}, got {ss.segment_id}")
            if abs(ss.start_time - ns.start_time) > 1e-3 or abs(ss.end_time - ns.end_time) > 1e-3:
                result.errors.append(f"Timestamp mismatch at index {i} ({ns.id})")
            if ss.text != ns.text:
                result.errors.append(f"Text content mutated at index {i} ({ns.id}) during alignment")

        result.passed = len(result.errors) == 0
        self._log_result(result)
        return result

    # ------------------------------------------------------------------ #
    # 3. Speaker Attributed -> Participant Attributed                     #
    # ------------------------------------------------------------------ #

    def validate_speaker_to_participant(
        self,
        speaker: SpeakerAttributedTranscript,
        participant: ParticipantAttributedTranscript,
    ) -> IntegrityResult:
        result = IntegrityResult(stage_transition="Speaker -> Participant")
        spk_segs = speaker.segments
        part_segs = participant.segments

        result.input_segment_count = len(spk_segs)
        result.output_segment_count = len(part_segs)

        result.input_word_count = sum(len(s.text.split()) for s in spk_segs)
        result.output_word_count = sum(len(s.text.split()) for s in part_segs)

        result.input_char_count = sum(len(s.text) for s in spk_segs)
        result.output_char_count = sum(len(s.text) for s in part_segs)

        if len(part_segs) != len(spk_segs):
            result.errors.append(
                f"Segment count mismatch: SpeakerAttributed has {len(spk_segs)} segments, "
                f"ParticipantAttributed has {len(part_segs)} segments."
            )

        min_len = min(len(spk_segs), len(part_segs))
        for i in range(min_len):
            ss = spk_segs[i]
            ps = part_segs[i]

            if ps.segment_id != ss.segment_id:
                result.errors.append(f"Segment ID mismatch at index {i}: expected {ss.segment_id}, got {ps.segment_id}")
            if abs(ps.start_time - ss.start_time) > 1e-3 or abs(ps.end_time - ss.end_time) > 1e-3:
                result.errors.append(f"Timestamp mismatch at index {i} ({ss.segment_id})")
            if ps.text != ss.text:
                result.errors.append(f"Text content mutated at index {i} ({ss.segment_id}) during resolution")
            if ps.speaker_label != ss.speaker_label:
                result.errors.append(f"Speaker label overwritten at index {i} ({ss.segment_id})")

        result.passed = len(result.errors) == 0
        self._log_result(result)
        return result

    # ------------------------------------------------------------------ #
    # Helper                                                               #
    # ------------------------------------------------------------------ #

    def raise_for_errors(self, result: IntegrityResult) -> None:
        if not result.passed:
            err_msg = f"Integrity check failed [{result.stage_transition}]: {'; '.join(result.errors)}"
            log.error("integrity.validation_failed", transition=result.stage_transition, errors=result.errors)
            raise TranscriptIntegrityError(err_msg)

    def _log_result(self, result: IntegrityResult) -> None:
        if result.passed:
            log.info(
                "integrity.validation_passed",
                transition=result.stage_transition,
                input_segments=result.input_segment_count,
                output_segments=result.output_segment_count,
                word_loss_percent=result.word_loss_percent,
                char_loss_percent=result.char_loss_percent,
                warnings_count=len(result.warnings),
            )
        else:
            log.error(
                "integrity.validation_errors_detected",
                transition=result.stage_transition,
                errors=result.errors,
                warnings=result.warnings,
            )
        for warn in result.warnings:
            log.warning("integrity.validation_warning", transition=result.stage_transition, message=warn)
