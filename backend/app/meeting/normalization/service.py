"""TranscriptNormalizationService.

Implements TranscriptNormalizer. Consumes a RawTranscript and produces
a NormalizedTranscript. Zero AI calls, zero network calls. Deterministic.

Architectural contract:
  - Text-cleaning ONLY. Timestamps, IDs, ordering, speaker, language,
    and confidence are never modified.
  - Segment count is preserved except for whitespace-only empty segments
    which are removed.
  - Boundary integrity is enforced by the pipeline and will raise
    TranscriptNormalizationError if violated.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import List

from app.meeting.artifacts.transcript import (
    NormalizedTranscript,
    NormalizedTranscriptSegment,
    NormalizationStatistics,
    RawTranscript,
    TranscriptSegment,
)
from app.meeting.config import meeting_config
from app.meeting.contracts.transcript import TranscriptNormalizer
from app.meeting.exceptions import TranscriptNormalizationError
from app.meeting.logger import get_logger
from app.meeting.normalization.pipeline import NormalizationPipeline
from app.meeting.normalization.rules.base import NormalizationRule
from app.meeting.normalization.rules.capitalization import CapitalizationRule
from app.meeting.normalization.rules.duplicate_words import DuplicateWordRule
from app.meeting.normalization.rules.empty_segment import EmptySegmentRule
from app.meeting.normalization.rules.filler_words import FillerWordRule
from app.meeting.normalization.rules.punctuation import PunctuationRule
from app.meeting.normalization.rules.repeated_chars import RepeatedCharRule
from app.meeting.normalization.rules.whitespace import WhitespaceRule

log = get_logger("normalization.service")


def _build_rules() -> List[NormalizationRule]:
    """Construct the ordered rule list from configuration.

    This is the only place where rules are ordered.  Adding or removing a rule
    requires changing only this function.

    Segment merging is intentionally excluded. See segment_merge.py for rationale.
    """
    rules: List[NormalizationRule] = [
        WhitespaceRule(),
        EmptySegmentRule(),
    ]

    if meeting_config.NORMALIZATION_ENABLE_DUPLICATE_REMOVAL:
        rules.append(DuplicateWordRule())

    if meeting_config.NORMALIZATION_ENABLE_REPEATED_CHARS:
        rules.append(RepeatedCharRule())

    if meeting_config.NORMALIZATION_ENABLE_PUNCTUATION:
        rules.append(PunctuationRule())

    if meeting_config.NORMALIZATION_ENABLE_CAPITALIZATION:
        rules.append(CapitalizationRule())

    if meeting_config.NORMALIZATION_ENABLE_FILLER_REMOVAL:
        rules.append(FillerWordRule())

    return rules


def _to_normalized_segment(
    seg: TranscriptSegment,
    language: str,
) -> NormalizedTranscriptSegment:
    """Project a TranscriptSegment to NormalizedTranscriptSegment.

    Drops STT-specific fields (avg_logprob, compression_ratio, etc.).
    Preserves: id, speaker, language, timestamps, confidence.
    """
    text = seg.text or ""
    words = text.split()
    seg_lang = seg.detected_language if seg.detected_language != "unknown" else language
    return NormalizedTranscriptSegment(
        id=f"norm_{seg.id}",
        meeting_id=seg.meeting_id,
        start_time=seg.start_time,
        end_time=seg.end_time,
        text=text,
        speaker=seg.speaker,
        language=seg_lang,
        confidence=seg.confidence,
        word_count=len(words),
        character_count=len(text),
    )


class TranscriptNormalizationService(TranscriptNormalizer):
    """Deterministic transcript normalization pipeline.

    Consumes:  RawTranscript
    Produces:  NormalizedTranscript

    No AI, no network, no external services.
    """

    async def normalize(self, raw: RawTranscript) -> NormalizedTranscript:
        start_time = time.monotonic()
        start_dt = datetime.now(timezone.utc)

        log.info(
            "meeting.normalization.started",
            meeting_id=raw.meeting_id,
            artifact_id=raw.id,
            input_segments=len(raw.segments),
            language=raw.detected_language,
        )

        try:
            rules = _build_rules()
            pipeline = NormalizationPipeline(rules)

            for rule in rules:
                log.info(
                    "meeting.normalization.rule.started",
                    meeting_id=raw.meeting_id,
                    rule_name=rule.name,
                )

            # Project RawTranscript segments → NormalizedTranscriptSegment
            input_segments = [
                _to_normalized_segment(s, raw.detected_language)
                for s in raw.segments
            ]

            # Execute — raises TranscriptNormalizationError on integrity violation
            output_segments, rule_stats, empty_removed = pipeline.run(input_segments)

        except TranscriptNormalizationError:
            raise
        except Exception as exc:
            log.error(
                "meeting.normalization.rule.failed",
                meeting_id=raw.meeting_id,
                error=str(exc),
            )
            raise TranscriptNormalizationError(
                f"Normalization pipeline failed: {exc}"
            ) from exc

        end_time = time.monotonic()
        end_dt = datetime.now(timezone.utc)
        duration_ms = int((end_time - start_time) * 1000)

        avg_len = (
            sum(len(s.text) for s in output_segments) / len(output_segments)
            if output_segments
            else 0.0
        )

        stats = NormalizationStatistics(
            meeting_id=raw.meeting_id,
            rule_statistics=rule_stats,
            total_input_segments=len(input_segments),
            total_output_segments=len(output_segments),
            removed_segments=empty_removed,
            merged_segments=0,  # merging is disabled — always 0
            processing_time_ms=duration_ms,
            average_segment_length=round(avg_len, 2),
        )

        artifact = NormalizedTranscript(
            meeting_id=raw.meeting_id,
            parent_raw_transcript_id=raw.id,
            language=raw.detected_language,
            processing_version=meeting_config.NORMALIZATION_PROCESSING_VERSION,
            normalization_started_at=start_dt.isoformat(),
            normalization_completed_at=end_dt.isoformat(),
            normalization_duration_ms=duration_ms,
            segments=output_segments,
            statistics=stats,
        )

        log.info(
            "meeting.normalization.completed",
            meeting_id=raw.meeting_id,
            artifact_id=artifact.id,
            input_segments=len(input_segments),
            output_segments=len(output_segments),
            removed_segments=empty_removed,
            merged_segments=0,
            duration_ms=duration_ms,
            rule_statistics=rule_stats,
        )
        log.info(
            "meeting.artifact.generated",
            artifact_type="NormalizedTranscript",
            artifact_id=artifact.id,
            meeting_id=raw.meeting_id,
        )

        return artifact
