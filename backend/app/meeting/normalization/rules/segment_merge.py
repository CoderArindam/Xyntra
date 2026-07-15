"""Segment merge utility — DEPRECATED, not part of the normalization pipeline.

Segment merging is intentionally disabled from the normalization stage.

Transcript boundaries are produced by the STT provider (Whisper, Groq, etc.)
and must remain immutable through normalization and into speaker attribution.
Merging segments here would destroy diarization alignment, break timestamp
precision, and corrupt speaker attribution.

This module is preserved for potential future use in a SEPARATE rendering
layer that runs AFTER ParticipantAttributedTranscript has been produced.
Any such rendering layer must operate on a copy and must never modify the
canonical NormalizedTranscript artifact.

DO NOT import this module from NormalizationPipeline or NormalizationService.
"""
from __future__ import annotations

import uuid
from typing import List, Tuple

from app.meeting.artifacts.transcript import NormalizedTranscriptSegment
from app.meeting.config import meeting_config


def merge_segments(
    segments: List[NormalizedTranscriptSegment],
) -> Tuple[List[NormalizedTranscriptSegment], int]:
    """Merge eligible adjacent segments.

    Returns:
        (merged_list, merge_count)
    """
    if not segments:
        return [], 0

    max_gap_sec = meeting_config.NORMALIZATION_MAX_SEGMENT_GAP_MS / 1000.0
    max_len = meeting_config.NORMALIZATION_MAX_SEGMENT_LENGTH

    result: List[NormalizedTranscriptSegment] = []
    merge_count = 0
    current = segments[0]

    for next_seg in segments[1:]:
        gap = next_seg.start_time - current.end_time
        combined_text = current.text.rstrip(".") + ". " + next_seg.text
        same_speaker = current.speaker == next_seg.speaker
        same_language = current.language == next_seg.language

        can_merge = (
            same_speaker
            and same_language
            and gap >= 0  # no overlap
            and gap <= max_gap_sec
            and len(combined_text) <= max_len
        )

        if can_merge:
            # Propagate lower confidence (more conservative)
            merged_confidence: float | None = None
            if current.confidence is not None and next_seg.confidence is not None:
                merged_confidence = min(current.confidence, next_seg.confidence)
            elif current.confidence is not None:
                merged_confidence = current.confidence
            elif next_seg.confidence is not None:
                merged_confidence = next_seg.confidence

            words = combined_text.split()
            current = NormalizedTranscriptSegment(
                id=f"merged_{uuid.uuid4().hex[:8]}",
                meeting_id=current.meeting_id,
                start_time=current.start_time,
                end_time=next_seg.end_time,
                text=combined_text,
                speaker=current.speaker,
                language=current.language,
                confidence=merged_confidence,
                word_count=len(words),
                character_count=len(combined_text),
                metadata={**current.metadata, "merged": True},
            )
            merge_count += 1
        else:
            result.append(current)
            current = next_seg

    result.append(current)
    return result, merge_count
