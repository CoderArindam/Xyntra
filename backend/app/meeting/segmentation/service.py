"""ConversationTurnSegmenter — intelligent conversation turn segmentation layer.

Consumes a NormalizedTranscript and splits merged multi-speaker segments into
sentence-level turn candidates before speaker alignment and participant attribution.

Design Principles:
  - Deterministic, fast (O(n)), zero AI calls, zero network calls.
  - Sentence-boundary splitting only (. ? ! ।) — never split mid-word.
  - Proportional timestamp distribution by character count.
  - Heuristic dialogue alternation detection (Question → Answer, Command → Response, Acknowledgements).
  - Attaches candidate_speaker_switch=true and speaker_switch_reason to candidate turns.
  - Protects confident short segments (< 5s, single sentence) without dialogue markers.
  - Full traceability and metadata preservation.
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Set

from app.meeting.artifacts.transcript import (
    NormalizedTranscript,
    NormalizedTranscriptSegment,
    SegmentationStatistics,
)
from app.meeting.config import meeting_config
from app.meeting.logger import get_logger

log = get_logger("segmentation.service")

# Punctuation regex for sentence splitting (. ? ! ।)
_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.?!।])\s+")

# Acknowledgement / dialogue response phrases (case-insensitive)
_ACKNOWLEDGEMENTS: Set[str] = {
    "yes", "okay", "sure", "exactly", "right", "no", "hmm", "hm", "yeah", "yep", "nope",
    "got it", "thanks", "thank you", "yes sir", "no sir", "fine", "understood", "true",
    "i know", "ok", "haan", "thik hai", "sahi", "thik ache", "dhanyabad", "dhanyavaad",
    "have a good day", "bye", "goodbye", "see you"
}

# Question prefix words
_QUESTION_WORDS: Set[str] = {
    "how", "what", "why", "who", "where", "when", "can", "could", "would", "should",
    "is", "are", "do", "does", "did", "kyun", "kya", "kaise", "kahan", "keeno", "kine"
}

# Imperative / Command prefix words
_COMMAND_WORDS: Set[str] = {
    "please", "kindly", "finish", "do", "tell", "send", "check", "make", "let's", "lets"
}


def _is_question(text: str) -> bool:
    clean = text.strip().lower()
    if clean.endswith("?"):
        return True
    words = clean.split()
    if words and words[0].rstrip(",.!") in _QUESTION_WORDS:
        return True
    return False


def _is_command(text: str) -> bool:
    clean = text.strip().lower()
    words = clean.split()
    if words and words[0].rstrip(",.!") in _COMMAND_WORDS:
        return True
    return False


def _is_acknowledgement(text: str) -> bool:
    clean = re.sub(r"[^\w\s]", "", text.strip().lower())
    return clean in _ACKNOWLEDGEMENTS or (len(clean.split()) <= 3 and clean in _ACKNOWLEDGEMENTS)


def _split_into_sentences(text: str) -> List[str]:
    """Split text into sentences cleanly on punctuation boundaries."""
    raw_splits = _SENTENCE_SPLIT_PATTERN.split(text.strip())
    sentences = [s.strip() for s in raw_splits if s and s.strip()]
    return sentences if sentences else ([text.strip()] if text.strip() else [])


def _should_split(seg: NormalizedTranscriptSegment) -> bool:
    """Determine if a segment is a candidate for multi-speaker splitting."""
    duration = seg.end_time - seg.start_time
    text = seg.text.strip()
    sentences = _split_into_sentences(text)

    # Protection Rule: Confident, short single sentence (< 5s) without dialogue markers
    if (
        duration < meeting_config.SEGMENTATION_MIN_UNTOUCHED_DURATION_SEC
        and len(sentences) <= 1
        and not _is_acknowledgement(text)
        and not _is_question(text)
    ):
        return False

    # Splitting Criteria
    is_large_duration = duration >= meeting_config.SEGMENTATION_MAX_DURATION_SEC
    is_long_text = len(text) >= meeting_config.SEGMENTATION_MAX_CHARACTERS
    has_multiple_sentences = len(sentences) > 1

    return is_large_duration or is_long_text or has_multiple_sentences


class ConversationTurnSegmenter:
    """Splits merged multi-speaker segments into sentence-level conversation turns."""

    def segment(self, transcript: NormalizedTranscript) -> NormalizedTranscript:
        t0 = time.monotonic()
        start_dt = datetime.now(timezone.utc)

        input_segments = transcript.segments
        input_count = len(input_segments)

        durations_before = [s.end_time - s.start_time for s in input_segments]
        avg_dur_before = (sum(durations_before) / input_count) if input_count > 0 else 0.0

        log.info(
            "segmentation.started",
            meeting_id=transcript.meeting_id,
            input_segments=input_count,
            avg_duration_before=round(avg_dur_before, 2),
        )

        output_segments: List[NormalizedTranscriptSegment] = []
        segments_split_count = 0
        candidate_switches_count = 0

        for parent_seg in input_segments:
            if not _should_split(parent_seg):
                output_segments.append(parent_seg)
                continue

            sentences = _split_into_sentences(parent_seg.text)
            if len(sentences) <= 1:
                output_segments.append(parent_seg)
                continue

            segments_split_count += 1
            parent_dur = parent_seg.end_time - parent_seg.start_time
            total_chars = sum(len(s) for s in sentences)

            curr_start = parent_seg.start_time
            split_units: List[NormalizedTranscriptSegment] = []

            for idx, sent in enumerate(sentences):
                char_ratio = (len(sent) / total_chars) if total_chars > 0 else (1.0 / len(sentences))
                sent_dur = parent_dur * char_ratio

                sent_start = round(curr_start, 2)
                # Ensure the last sentence ends exactly on parent_seg.end_time
                if idx == len(sentences) - 1:
                    sent_end = parent_seg.end_time
                else:
                    sent_end = round(curr_start + sent_dur, 2)

                curr_start = sent_end
                sent_words = sent.split()

                new_id = f"{parent_seg.id}_s{idx}"
                raw_id = parent_seg.raw_segment_id or parent_seg.id.replace("norm_", "")

                history = list(parent_seg.processing_history)
                if "turn_segmentation" not in history:
                    history.append("turn_segmentation")

                split_seg = NormalizedTranscriptSegment(
                    id=new_id,
                    raw_segment_id=raw_id,
                    source_stage="segmentation",
                    processing_history=history,
                    meeting_id=parent_seg.meeting_id,
                    start_time=sent_start,
                    end_time=sent_end,
                    text=sent,
                    speaker=parent_seg.speaker,
                    language=parent_seg.language,
                    confidence=parent_seg.confidence,
                    word_count=len(sent_words),
                    character_count=len(sent),
                    metadata=dict(parent_seg.metadata),
                )
                split_units.append(split_seg)

            output_segments.extend(split_units)

        # Check if the transcript has multiple unique speakers detected by the STT
        unique_speakers = {s.speaker for s in output_segments if s.speaker}
        has_multiple_speakers = len(unique_speakers) > 1

        # Analyze dialogue alternation across all output segments
        for i in range(1, len(output_segments)):
            prev_u = output_segments[i - 1]
            curr_u = output_segments[i]

            # Do not assume speaker switches within sentence units of the same parent segment
            if prev_u.raw_segment_id and curr_u.raw_segment_id and prev_u.raw_segment_id == curr_u.raw_segment_id:
                continue

            switch_detected = False
            reason: Optional[str] = None

            if has_multiple_speakers:
                # If diarization is available, rely on speaker label changes
                if prev_u.speaker and curr_u.speaker and prev_u.speaker != curr_u.speaker:
                    switch_detected = True
                    reason = "speaker_label_change"
            else:
                # Fallback to conversational heuristics if diarization is not available (e.g., mixed mono channel)
                # Rule 1: Question → Answer
                if _is_question(prev_u.text) and not _is_question(curr_u.text):
                    switch_detected = True
                    reason = "question_answer"

                # Rule 2: Command / Request → Response / Acknowledgement
                elif _is_command(prev_u.text) and (_is_acknowledgement(curr_u.text) or len(curr_u.text.split()) <= 4):
                    switch_detected = True
                    reason = "acknowledgement"

                # Rule 3: Acknowledgement / Short phrase alternation
                elif _is_acknowledgement(curr_u.text):
                    switch_detected = True
                    reason = "acknowledgement"

                elif len(prev_u.text) <= 25 and len(curr_u.text) <= 25:
                    switch_detected = True
                    reason = "alternating_short_sentence"

            if switch_detected and reason:
                curr_u.metadata["candidate_speaker_switch"] = True
                curr_u.metadata["speaker_switch_reason"] = reason
                candidate_switches_count += 1
                log.debug(
                    "segmentation.candidate_speaker_switch",
                    segment_id=curr_u.id,
                    reason=reason,
                    text=curr_u.text,
                )

        duration_ms = int((time.monotonic() - t0) * 1000)
        durations_after = [s.end_time - s.start_time for s in output_segments]
        avg_dur_after = (sum(durations_after) / len(output_segments)) if output_segments else 0.0

        stats = SegmentationStatistics(
            meeting_id=transcript.meeting_id,
            total_input_segments=input_count,
            total_output_segments=len(output_segments),
            segments_split=segments_split_count,
            average_duration_before=round(avg_dur_before, 2),
            average_duration_after=round(avg_dur_after, 2),
            candidate_switches_detected=candidate_switches_count,
            processing_time_ms=duration_ms,
        )

        artifact = NormalizedTranscript(
            meeting_id=transcript.meeting_id,
            parent_raw_transcript_id=transcript.parent_raw_transcript_id,
            language=transcript.language,
            processing_version=meeting_config.SEGMENTATION_PROCESSING_VERSION,
            normalization_started_at=start_dt.isoformat(),
            normalization_completed_at=datetime.now(timezone.utc).isoformat(),
            normalization_duration_ms=duration_ms,
            segments=output_segments,
            statistics=transcript.statistics,
        )

        log.info(
            "segmentation.completed",
            meeting_id=transcript.meeting_id,
            input_segments=input_count,
            output_segments=len(output_segments),
            segments_split=segments_split_count,
            candidate_switches=candidate_switches_count,
            duration_ms=duration_ms,
        )

        return artifact
