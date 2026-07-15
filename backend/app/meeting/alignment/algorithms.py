"""Pure speaker alignment algorithms.

No logging. No artifacts.
All functions are deterministic and independently unit-testable.

Performance goal: O(N log N) by avoiding O(N x M) nested iteration.
Uses a sweep-line interval matching approach to efficiently aggregate overlap.
"""
from __future__ import annotations

import collections
from typing import Any, Dict, List, Tuple, Optional

from app.meeting.artifacts.speaker import SpeakerTurn
from app.meeting.artifacts.transcript import NormalizedTranscriptSegment


def remove_micro_turns(
    turns: List[SpeakerTurn], min_dur_ms: int
) -> Tuple[List[SpeakerTurn], List[Dict[str, Any]]]:
    """Filter out turns shorter than min_dur_ms.

    Returns:
        (retained_turns, removed_diagnostics)
    """
    min_dur_sec = min_dur_ms / 1000.0
    retained = []
    diagnostics = []

    # Sort to be safe, though input should be ordered
    sorted_turns = sorted(turns, key=lambda t: t.start_time)

    for i, turn in enumerate(sorted_turns):
        dur = turn.end_time - turn.start_time
        if dur < min_dur_sec:
            diagnostics.append(
                {
                    "turn_index": i,
                    "speaker_label": turn.speaker_label,
                    "removed_duration_ms": round(dur * 1000),
                    "removed_reason": "micro_turn",
                }
            )
        else:
            retained.append(turn)

    return retained, diagnostics


def merge_adjacent_turns(
    turns: List[SpeakerTurn], gap_ms: int
) -> Tuple[List[SpeakerTurn], int]:
    """Merge consecutive turns by the same speaker if the gap <= gap_ms.

    Returns:
        (merged_turns, merge_count)
    """
    if not turns:
        return [], 0

    gap_sec = gap_ms / 1000.0
    # Must be sorted by start_time
    sorted_turns = sorted(turns, key=lambda t: t.start_time)

    merged = []
    merge_count = 0
    current = sorted_turns[0]

    for next_turn in sorted_turns[1:]:
        gap = next_turn.start_time - current.end_time
        same_speaker = current.speaker_label == next_turn.speaker_label

        if same_speaker and gap <= gap_sec:
            # Merge
            merge_count += 1
            # Propagate the lowest confidence to be conservative
            min_conf = min(current.diarization_confidence, next_turn.diarization_confidence)
            current = SpeakerTurn(
                speaker_label=current.speaker_label,
                start_time=current.start_time,
                end_time=max(current.end_time, next_turn.end_time),
                diarization_confidence=min_conf,
            )
        else:
            merged.append(current)
            current = next_turn

    merged.append(current)
    return merged, merge_count


def calculate_overlap(
    seg_start: float,
    seg_end: float,
    turn_start: float,
    turn_end: float,
) -> float:
    """Return the duration of overlap between a segment and a turn in seconds."""
    overlap_start = max(seg_start, turn_start)
    overlap_end = min(seg_end, turn_end)
    return max(0.0, overlap_end - overlap_start)


def calculate_alignment_score(
    overlap_dur: float,
    effective_seg_dur: float,
    speaker_speech_dur: float,
    seg_weight: float,
    spk_weight: float,
) -> Tuple[float, float, float]:
    """Calculate the dual-weighted alignment score.

    Returns:
        (segment_overlap_score, speaker_coverage_score, final_score)
    """
    seg_score = (overlap_dur / effective_seg_dur) if effective_seg_dur > 0 else 0.0
    spk_score = (overlap_dur / speaker_speech_dur) if speaker_speech_dur > 0 else 0.0
    final_score = (seg_weight * seg_score) + (spk_weight * spk_score)
    return seg_score, spk_score, final_score


def resolve_tie(
    speaker1: str,
    score1: float,
    dur1: float,
    first_overlap1: float,
    speaker2: str,
    score2: float,
    dur2: float,
    first_overlap2: float,
) -> bool:
    """Deterministic tie-breaker. Returns True if speaker1 beats speaker2."""
    if score1 > score2:
        return True
    if score1 < score2:
        return False

    # Tie 1: Absolute overlap duration
    if dur1 > dur2:
        return True
    if dur1 < dur2:
        return False

    # Tie 2: Earliest first overlap
    if first_overlap1 < first_overlap2:
        return True
    if first_overlap1 > first_overlap2:
        return False

    # Tie 3: Alphabetical speaker label
    return speaker1 < speaker2


def find_best_speaker(
    seg_start: float,
    seg_end: float,
    overlapping_turns: List[SpeakerTurn],
    seg_weight: float,
    spk_weight: float,
    threshold: float,
) -> Tuple[Optional[str], float, float, float]:
    """Find the best speaker for a given segment based on overlapping turns.

    overlapping_turns must be the subset of turns that actually overlap with
    the interval [seg_start, seg_end].

    Returns:
        (best_speaker, segment_overlap_score, speaker_coverage_score, final_score)
        Returns (None, 0.0, 0.0, 0.0) if no speaker exceeds the threshold.
    """
    if not overlapping_turns:
        return None, 0.0, 0.0, 0.0

    # 1. Aggregate overlap by speaker, and find first overlap time per speaker
    speaker_overlap_dur: Dict[str, float] = collections.defaultdict(float)
    speaker_total_dur: Dict[str, float] = collections.defaultdict(float)
    speaker_first_overlap: Dict[str, float] = {}

    for turn in overlapping_turns:
        overlap = calculate_overlap(seg_start, seg_end, turn.start_time, turn.end_time)
        if overlap <= 0:
            continue

        spk = turn.speaker_label
        speaker_overlap_dur[spk] += overlap
        speaker_total_dur[spk] += (turn.end_time - turn.start_time)

        overlap_start = max(seg_start, turn.start_time)
        if spk not in speaker_first_overlap or overlap_start < speaker_first_overlap[spk]:
            speaker_first_overlap[spk] = overlap_start

    if not speaker_overlap_dur:
        return None, 0.0, 0.0, 0.0

    # 2. Compute effective speech duration in the segment (excluding silence)
    # This is simply the union of all overlapping turn intervals clamped to the segment.
    # We can do this by merging the clamped intervals and summing their lengths.
    clamped_intervals = []
    for turn in overlapping_turns:
        c_start = max(seg_start, turn.start_time)
        c_end = min(seg_end, turn.end_time)
        if c_start < c_end:
            clamped_intervals.append((c_start, c_end))

    clamped_intervals.sort(key=lambda x: x[0])
    effective_seg_dur = 0.0
    if clamped_intervals:
        curr_s, curr_e = clamped_intervals[0]
        for s, e in clamped_intervals[1:]:
            if s <= curr_e:
                curr_e = max(curr_e, e)
            else:
                effective_seg_dur += (curr_e - curr_s)
                curr_s, curr_e = s, e
        effective_seg_dur += (curr_e - curr_s)

    if effective_seg_dur <= 0:
        return None, 0.0, 0.0, 0.0

    # 3. Score and find best
    best_speaker = None
    best_seg_score = 0.0
    best_spk_score = 0.0
    best_final_score = 0.0
    best_dur = 0.0
    best_first = float("inf")

    for spk, overlap_dur in speaker_overlap_dur.items():
        spk_total_dur = speaker_total_dur[spk]
        seg_sc, spk_sc, final_sc = calculate_alignment_score(
            overlap_dur, effective_seg_dur, spk_total_dur, seg_weight, spk_weight
        )

        first_ov = speaker_first_overlap[spk]

        if best_speaker is None or resolve_tie(
            spk, final_sc, overlap_dur, first_ov,
            best_speaker, best_final_score, best_dur, best_first
        ):
            best_speaker = spk
            best_seg_score = seg_sc
            best_spk_score = spk_sc
            best_final_score = final_sc
            best_dur = overlap_dur
            best_first = first_ov

    if best_final_score >= threshold:
        return best_speaker, round(best_seg_score, 4), round(best_spk_score, 4), round(best_final_score, 4)

    return None, 0.0, 0.0, 0.0


def validate_timeline(turns: List[SpeakerTurn]) -> List[str]:
    """Validate SpeakerTimeline structural invariants.

    Returns a list of error messages. Empty list means valid.
    """
    errors: List[str] = []
    for i, turn in enumerate(turns):
        if turn.start_time < 0:
            errors.append(f"Turn {i}: negative start_time {turn.start_time}")
        if turn.end_time < 0:
            errors.append(f"Turn {i}: negative end_time {turn.end_time}")
        if turn.end_time <= turn.start_time:
            errors.append(
                f"Turn {i}: end_time ({turn.end_time}) <= start_time ({turn.start_time})"
            )
    return errors


def validate_segments(segments: List[NormalizedTranscriptSegment]) -> List[str]:
    """Validate transcript segment structural invariants.

    Returns a list of error messages. Empty list means valid.
    """
    errors: List[str] = []
    for i, seg in enumerate(segments):
        if seg.start_time < 0:
            errors.append(
                f"Segment {i} ({seg.id}): negative start_time {seg.start_time}"
            )
        if seg.end_time < 0:
            errors.append(
                f"Segment {i} ({seg.id}): negative end_time {seg.end_time}"
            )
        if seg.end_time <= seg.start_time:
            errors.append(
                f"Segment {i} ({seg.id}): end_time ({seg.end_time}) <= start_time ({seg.start_time})"
            )
    return errors
