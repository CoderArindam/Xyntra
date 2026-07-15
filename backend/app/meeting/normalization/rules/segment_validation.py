"""Segment validation rule — list-level.

Validates structural invariants and removes segments that violate them:
  - end_time > start_time
  - text is not empty
  - no timestamp overlaps with the previous segment
"""
from __future__ import annotations

from typing import List, Tuple

from app.meeting.artifacts.transcript import NormalizedTranscriptSegment


def validate_segments(
    segments: List[NormalizedTranscriptSegment],
) -> Tuple[List[NormalizedTranscriptSegment], int]:
    """Remove structurally invalid segments.

    Returns:
        (valid_list, removed_count)
    """
    valid: List[NormalizedTranscriptSegment] = []
    removed = 0
    prev_end = -1.0

    for seg in segments:
        if seg.end_time <= seg.start_time:
            removed += 1
            continue
        if not seg.text or not seg.text.strip():
            removed += 1
            continue
        if seg.start_time < prev_end:
            # Overlaps with previous — discard
            removed += 1
            continue
        valid.append(seg)
        prev_end = seg.end_time

    return valid, removed
