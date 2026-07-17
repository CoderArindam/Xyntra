"""SpeakerAlignmentService — M2.6.1 Speaker Alignment Engine.

Combines a NormalizedTranscript with a SpeakerTimeline to produce a
SpeakerAttributedTranscript using robust dual-scored overlap matching.

Anonymous speaker labels only (Speaker_00, Speaker_01…).
No participant names. No AI. Pure deterministic alignment.

Business logic lives in algorithms.py — this class handles:
  - input validation
  - turn pre-processing (merge & filter micro-turns)
  - algorithm invocation
  - artifact construction
  - statistics collection
  - structured logging
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import List, Optional

from app.meeting.alignment.algorithms import (
    find_best_speaker,
    merge_adjacent_turns,
    remove_micro_turns,
    validate_segments,
    validate_timeline,
)
from app.meeting.artifacts.speaker import (
    SpeakerAttributedSegment,
    SpeakerAttributedTranscript,
    SpeakerTimeline,
)
from app.meeting.artifacts.transcript import NormalizedTranscript
from app.meeting.config import meeting_config
from app.meeting.contracts.speaker_alignment import SpeakerAlignmentProvider
from app.meeting.exceptions import SpeakerAlignmentError
from app.meeting.logger import get_logger

log = get_logger("alignment.service")


class SpeakerAlignmentService(SpeakerAlignmentProvider):
    """Deterministic timestamp-based speaker alignment with pre-processing."""

    async def align(
        self,
        transcript: NormalizedTranscript,
        timeline: Optional[SpeakerTimeline],
    ) -> SpeakerAttributedTranscript:
        log.info(
            "alignment.started",
            meeting_id=transcript.meeting_id,
            transcript_id=transcript.id,
            timeline_id=timeline.id if timeline else None,
            segment_count=len(transcript.segments),
            turn_count=len(timeline.turns) if timeline else 0,
        )

        start_dt = datetime.now(timezone.utc)
        t0 = time.monotonic()

        # Track extended stats
        micro_turns_removed = 0
        turns_merged = 0
        total_final_score = 0.0

        try:
            # ---------------------------------------------------------- #
            # Validate inputs                                             #
            # ---------------------------------------------------------- #
            seg_errors = validate_segments(transcript.segments)
            if seg_errors:
                raise SpeakerAlignmentError(
                    f"Invalid transcript segments: {'; '.join(seg_errors)}"
                )

            turns = []
            if timeline:
                turn_errors = validate_timeline(timeline.turns)
                if turn_errors:
                    raise SpeakerAlignmentError(
                        f"Invalid speaker timeline: {'; '.join(turn_errors)}"
                    )
                turns = list(timeline.turns)  # Working copy

                # ---------------------------------------------------------- #
                # Pre-process turns (filter micro-turns, then merge)          #
                # ---------------------------------------------------------- #
                min_dur_ms = meeting_config.ALIGNMENT_MIN_TURN_DURATION_MS
                turns, removed_diagnostics = remove_micro_turns(turns, min_dur_ms)
                micro_turns_removed = len(removed_diagnostics)

                for diag in removed_diagnostics:
                    log.debug("alignment.micro_turn_removed", **diag)

                gap_ms = meeting_config.ALIGNMENT_MERGE_GAP_MS
                turns, turns_merged = merge_adjacent_turns(turns, gap_ms)

                if turns_merged > 0:
                    log.debug("alignment.turns_merged", count=turns_merged)

            # Configuration weights
            threshold = meeting_config.ALIGNMENT_OVERLAP_THRESHOLD
            seg_weight = meeting_config.ALIGNMENT_SCORE_SEGMENT_WEIGHT
            spk_weight = meeting_config.ALIGNMENT_SCORE_SPEAKER_WEIGHT

            # ---------------------------------------------------------- #
            # Align each segment                                          #
            # ---------------------------------------------------------- #
            attributed_segments: List[SpeakerAttributedSegment] = []
            matched = 0
            unmatched = 0

            # Optimisation: Sort turns for O(N log N) sweep mapping, but for simplicity
            # in this layer we pass the filtered turns array to the algorithm. 
            # The algorithm uses an overlapping interval subset.
            # We build an interval subset per segment to avoid O(N x M) entirely.
            # Assuming turns are sorted by start_time:
            turns.sort(key=lambda t: t.start_time)
            
            # Simple two-pointer / sweep approach to find overlapping turns per segment
            # so we only pass the actually relevant turns to `find_best_speaker`.
            turn_idx = 0
            num_turns = len(turns)

            for seg in transcript.segments:
                overlapping_turns = []
                
                # Advance turn_idx so it starts at the first potentially overlapping turn
                while turn_idx < num_turns and turns[turn_idx].end_time <= seg.start_time:
                    turn_idx += 1
                
                # Collect all turns that overlap with this segment
                curr_idx = turn_idx
                while curr_idx < num_turns and turns[curr_idx].start_time < seg.end_time:
                    overlapping_turns.append(turns[curr_idx])
                    curr_idx += 1

                best_speaker, seg_score, spk_score, final_score = find_best_speaker(
                    seg.start_time, seg.end_time, overlapping_turns,
                    seg_weight, spk_weight, threshold
                )

                if best_speaker is not None:
                    matched += 1
                    total_final_score += final_score
                    log.debug(
                        "alignment.segment_matched",
                        segment_id=seg.id,
                        speaker_label=best_speaker,
                        final_score=final_score,
                        seg_score=seg_score,
                        spk_score=spk_score,
                    )
                    
                    # We need the original diarization confidence for this speaker.
                    # As an approximation since we aggregated, take the max confidence 
                    # from the overlapping turns belonging to the best_speaker.
                    diar_conf = max(
                        [t.diarization_confidence for t in overlapping_turns if t.speaker_label == best_speaker],
                        default=1.0
                    )
                else:
                    unmatched += 1
                    diar_conf = None
                    log.debug(
                        "alignment.segment_unmatched",
                        segment_id=seg.id,
                        start_time=seg.start_time,
                        end_time=seg.end_time,
                    )

                attributed_segments.append(
                    SpeakerAttributedSegment(
                        segment_id=seg.id,
                        raw_segment_id=seg.raw_segment_id,
                        source_stage="alignment",
                        processing_history=[*seg.processing_history, "speaker_alignment"],
                        start_time=seg.start_time,
                        end_time=seg.end_time,
                        text=seg.text,
                        speaker_label=best_speaker,
                        diarization_confidence=diar_conf,
                        attribution_confidence=final_score if best_speaker else None,
                        confidence=seg.confidence,
                        language=seg.language,
                        metadata=dict(seg.metadata),
                    )
                )

        except SpeakerAlignmentError:
            log.error(
                "alignment.failed",
                meeting_id=transcript.meeting_id,
            )
            raise
        except Exception as exc:
            log.error(
                "alignment.failed",
                meeting_id=transcript.meeting_id,
                error=str(exc),
            )
            raise SpeakerAlignmentError(f"Speaker alignment failed: {exc}") from exc

        end_dt = datetime.now(timezone.utc)
        duration_ms = int((time.monotonic() - t0) * 1000)
        avg_overlap = round(total_final_score / matched, 4) if matched > 0 else 0.0

        artifact = SpeakerAttributedTranscript(
            meeting_id=transcript.meeting_id,
            parent_normalized_transcript_id=transcript.id,
            parent_speaker_timeline_id=timeline.id if timeline else None,
            segments=attributed_segments,
            unattributed_segment_count=unmatched,
            attribution_started_at=start_dt.isoformat(),
            attribution_completed_at=end_dt.isoformat(),
            attribution_duration_ms=duration_ms,
            processing_version=meeting_config.ALIGNMENT_PROCESSING_VERSION,
        )

        from app.meeting.normalization.validator import TranscriptIntegrityValidator
        validator = TranscriptIntegrityValidator()
        integrity_res = validator.validate_normalized_to_speaker(transcript, artifact)
        validator.raise_for_errors(integrity_res)

        log.info(
            "alignment.completed",
            meeting_id=transcript.meeting_id,
            artifact_id=artifact.id,
            total_segments=len(attributed_segments),
            matched_segments=matched,
            unmatched_segments=unmatched,
            average_confidence=avg_overlap,
            micro_turns_removed=micro_turns_removed,
            turns_merged=turns_merged,
            duration_ms=duration_ms,
        )
        log.info(
            "meeting.artifact.generated",
            artifact_type="SpeakerAttributedTranscript",
            artifact_id=artifact.id,
            meeting_id=transcript.meeting_id,
        )

        return artifact
