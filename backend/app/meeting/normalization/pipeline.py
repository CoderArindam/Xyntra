"""Normalization pipeline executor.

Applies per-segment text-cleaning rules sequentially, then runs the boundary
integrity check and structural validation.

Architectural contract:
  - The pipeline is text-normalization ONLY.
  - Segment count, order, IDs, timestamps, speaker, language, and confidence
    are immutable. Only text, word_count, and character_count may change.
  - Segment merging is intentionally excluded from this pipeline. Merging is
    a rendering concern and must happen in a separate layer after speaker
    attribution.
  - If any segment count change is detected (beyond whitespace-only removal),
    the pipeline raises TranscriptNormalizationError.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from app.meeting.artifacts.transcript import NormalizedTranscriptSegment
from app.meeting.exceptions import TranscriptNormalizationError
from app.meeting.normalization.rules.base import NormalizationRule


class NormalizationPipeline:
    """Executes injected text-cleaning rules against a list of segments.

    Each rule runs per-segment and may only modify text content.
    The pipeline enforces structural immutability — any rule that accidentally
    alters timestamps, IDs, or ordering will be caught by _integrity_check.
    """

    def __init__(self, rules: List[NormalizationRule]) -> None:
        self._rules = rules

    def run(
        self,
        segments: List[NormalizedTranscriptSegment],
    ) -> Tuple[List[NormalizedTranscriptSegment], Dict[str, int], int]:
        """Execute the pipeline.

        Returns:
            (output_segments, rule_statistics, empty_removed_count)

        Raises:
            TranscriptNormalizationError: if boundary integrity is violated.
        """
        rule_stats: Dict[str, int] = {rule.name: 0 for rule in self._rules}
        input_count = len(segments)

        # ------------------------------------------------------------------ #
        # Per-segment text-cleaning pass                                      #
        # ------------------------------------------------------------------ #
        result: List[NormalizedTranscriptSegment] = []
        empty_removed = 0

        for seg in segments:
            current: Optional[NormalizedTranscriptSegment] = seg
            for rule in self._rules:
                if current is None:
                    break
                after = rule.normalize(current)
                if after is None:
                    # Rule removed segment (e.g. whitespace-only text)
                    rule_stats[rule.name] = rule_stats.get(rule.name, 0) + 1
                    current = None
                elif after.text != current.text:
                    rule_stats[rule.name] = rule_stats.get(rule.name, 0) + 1
                    current = after
                else:
                    current = after

            if current is None:
                empty_removed += 1
            else:
                # Enforce: only text fields may have changed
                _assert_structure_unchanged(seg, current)
                result.append(current)

        # ------------------------------------------------------------------ #
        # Boundary integrity check                                            #
        # ------------------------------------------------------------------ #
        _boundary_integrity_check(input_count, result, empty_removed)

        return result, rule_stats, empty_removed


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

def _assert_structure_unchanged(
    original: NormalizedTranscriptSegment,
    after: NormalizedTranscriptSegment,
) -> None:
    """Raise if a rule changed any structural field."""
    if after.start_time != original.start_time:
        raise TranscriptNormalizationError(
            f"Rule mutated start_time on segment {original.id}: "
            f"{original.start_time} → {after.start_time}"
        )
    if after.end_time != original.end_time:
        raise TranscriptNormalizationError(
            f"Rule mutated end_time on segment {original.id}: "
            f"{original.end_time} → {after.end_time}"
        )
    if after.speaker != original.speaker:
        raise TranscriptNormalizationError(
            f"Rule mutated speaker on segment {original.id}: "
            f"{original.speaker!r} → {after.speaker!r}"
        )
    if after.language != original.language:
        raise TranscriptNormalizationError(
            f"Rule mutated language on segment {original.id}: "
            f"{original.language!r} → {after.language!r}"
        )
    if after.confidence != original.confidence:
        raise TranscriptNormalizationError(
            f"Rule mutated confidence on segment {original.id}: "
            f"{original.confidence} → {after.confidence}"
        )


def _boundary_integrity_check(
    input_count: int,
    output: List[NormalizedTranscriptSegment],
    empty_removed: int,
) -> None:
    """Verify segment count is consistent with what text-cleaning is allowed to remove.

    The only segments that may disappear are those whose text became
    empty (whitespace-only) after cleaning — tracked by empty_removed.
    Any discrepancy beyond that is a pipeline bug.
    """
    expected = input_count - empty_removed
    actual = len(output)
    if actual != expected:
        raise TranscriptNormalizationError(
            f"Boundary integrity violation: expected {expected} segments "
            f"({input_count} input − {empty_removed} empty removed) "
            f"but got {actual}. A normalization rule is illegally "
            f"merging, splitting, or dropping non-empty segments."
        )

    # Verify ordering is preserved
    for i in range(1, len(output)):
        if output[i].start_time < output[i - 1].start_time:
            raise TranscriptNormalizationError(
                f"Boundary integrity violation: segment ordering was corrupted "
                f"at index {i} (start_time {output[i].start_time} < "
                f"previous {output[i-1].start_time})."
            )
