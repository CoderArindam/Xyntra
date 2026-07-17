"""Conversation State Engine (Phase 2.6).

Production-grade, deterministic, O(n) local conversation state attribution engine.
No LLM. No AI. No external APIs. No network calls. No language-specific keyword dictionaries.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set, Tuple

from app.meeting.artifacts.speaker import (
    SpeakerAttributedSegment,
    ParticipantAttributedSegment,
    MeetingParticipant,
    SpeakerMapping,
    ParticipantPresenceTimeline,
)
from app.meeting.artifacts.attribution_debug import (
    RuleTrace,
    CandidateScores,
    AttributionDecision,
    AttributionStatistics,
    AttributionTimelineItem,
    AttributionDebugArtifact,
    AttributionTimelineArtifact,
)
from app.meeting.attribution.conversation_state import ConversationState
from app.meeting.attribution.providers import (
    EvidenceProvider,
    PresenceEvidenceProvider,
    VocativeEvidenceProvider,
    TemporalContinuityProvider,
    ConversationalTransitionProvider,
    OwnershipProvider,
    AlternationProvider,
    InterruptionProvider,
    SegmentationProvider,
    DeepgramPriorProvider,
)
from app.meeting.config import meeting_config
from app.meeting.logger import get_logger

log = get_logger("attribution.state_engine")

# Minimum score advantage required to switch active speakers (prevents numerical noise oscillation)
_SWITCH_HYSTERESIS_MARGIN = 1.5


def _build_presence_intervals(
    participants: List[MeetingParticipant],
    presence_timeline: Optional[ParticipantPresenceTimeline] = None,
) -> Dict[str, Tuple[float, float]]:
    intervals: Dict[str, Tuple[float, float]] = {}

    rec_start = None
    if presence_timeline and presence_timeline.events:
        for ev in presence_timeline.events:
            try:
                dt = datetime.fromisoformat(ev.timestamp.replace("Z", "+00:00"))
                if rec_start is None or dt < rec_start:
                    rec_start = dt
            except Exception:
                continue

    for p in participants:
        join_sec = 0.0
        leave_sec = float("inf")

        if p.join_time:
            try:
                if rec_start:
                    dt = datetime.fromisoformat(p.join_time.replace("Z", "+00:00"))
                    join_sec = max(0.0, (dt - rec_start).total_seconds())
                elif p.join_time.replace(".", "", 1).isdigit():
                    join_sec = float(p.join_time)
            except Exception:
                pass

        if p.leave_time:
            try:
                if rec_start:
                    dt = datetime.fromisoformat(p.leave_time.replace("Z", "+00:00"))
                    leave_sec = (dt - rec_start).total_seconds()
                elif p.leave_time.replace(".", "", 1).isdigit():
                    leave_sec = float(p.leave_time)
            except Exception:
                pass

        if "join_sec" in p.metadata:
            join_sec = float(p.metadata["join_sec"])
        if "leave_sec" in p.metadata:
            leave_sec = float(p.metadata["leave_sec"])

        intervals[p.participant_id] = (join_sec, leave_sec)

    return intervals


class DynamicAttributionEngine:
    """Phase 2.6 Conversation State Attribution Engine."""

    def __init__(self):
        self.providers: List[EvidenceProvider] = [
            PresenceEvidenceProvider(),
            VocativeEvidenceProvider(),
            TemporalContinuityProvider(),
            ConversationalTransitionProvider(),
            OwnershipProvider(),
            AlternationProvider(),
            InterruptionProvider(),
            SegmentationProvider(),
            DeepgramPriorProvider(),
        ]

    def attribute(
        self,
        attributed_segments: List[SpeakerAttributedSegment],
        participants: List[MeetingParticipant],
        mapping: Optional[SpeakerMapping] = None,
        presence_timeline: Optional[ParticipantPresenceTimeline] = None,
        meeting_id: str = "unknown",
        parent_transcript_id: str = "unknown",
    ) -> Tuple[List[ParticipantAttributedSegment], AttributionDebugArtifact, AttributionTimelineArtifact]:
        t0 = time.monotonic()
        now_iso = datetime.now(timezone.utc).isoformat()

        if not participants:
            log.warning("attribution.state_engine.empty_roster")
            resolved = [
                ParticipantAttributedSegment(
                    segment_id=seg.segment_id,
                    raw_segment_id=seg.raw_segment_id,
                    source_stage="resolution",
                    processing_history=[*seg.processing_history, "conversation_state_attribution"],
                    start_time=seg.start_time,
                    end_time=seg.end_time,
                    text=seg.text,
                    speaker_label=seg.speaker_label,
                    speaker_label_confidence=seg.diarization_confidence,
                    participant_id=None,
                    participant_name=None,
                    mapping_confidence=None,
                    confidence=seg.confidence,
                    language=seg.language,
                    resolution_reason="no_participants_in_roster",
                    metadata=dict(seg.metadata),
                )
                for seg in attributed_segments
            ]
            empty_stats = AttributionStatistics(total_segments=len(resolved))
            debug_art = AttributionDebugArtifact(
                meeting_id=meeting_id,
                parent_speaker_attributed_transcript_id=parent_transcript_id,
                statistics=empty_stats,
                decisions=[],
                created_at=now_iso,
            )
            timeline_art = AttributionTimelineArtifact(
                meeting_id=meeting_id,
                parent_speaker_attributed_transcript_id=parent_transcript_id,
                timeline=[],
                created_at=now_iso,
            )
            return resolved, debug_art, timeline_art

        presence_intervals = _build_presence_intervals(participants, presence_timeline)

        static_map: Dict[str, Tuple[str, str, float]] = {}
        if mapping:
            for entry in mapping.entries:
                if entry.speaker_label and entry.participant_id:
                    static_map[entry.speaker_label] = (
                        entry.participant_id,
                        entry.participant_name or "",
                        entry.mapping_confidence,
                    )

        p_by_id: Dict[str, MeetingParticipant] = {p.participant_id: p for p in participants}

        unique_speakers = {s.speaker_label for s in attributed_segments if s.speaker_label}
        has_multiple_speakers = len(unique_speakers) > 1

        resolved_segments: List[ParticipantAttributedSegment] = []
        decisions: List[AttributionDecision] = []
        timeline_items: List[AttributionTimelineItem] = []

        # Tally counts for AttributionStatistics
        fallback_count = 0
        deepgram_count = 0
        dialogue_count = 0
        vocative_count = 0
        question_count = 0
        acknowledgement_count = 0
        continuity_count = 0
        total_confidence = 0.0
        total_gap = 0.0

        # Initialize ConversationState
        state = ConversationState()

        for idx, seg in enumerate(attributed_segments):
            candidate_scores_list: List[CandidateScores] = []

            for p in participants:
                pid = p.participant_id
                p_window = presence_intervals.get(pid, (0.0, float("inf")))

                scores_by_provider: Dict[str, float] = {}
                rule_traces: List[RuleTrace] = []
                total_cand_score = 0.0

                for prov in self.providers:
                    sc, trace = prov.evaluate(
                        segment=seg,
                        participant=p,
                        state=state,
                        presence_window=p_window,
                        static_map=static_map,
                        all_participants=participants,
                    )
                    scores_by_provider[prov.provider_name] = sc
                    rule_traces.append(trace)

                    if prov.provider_name == "PresenceWindow" and sc < 0.0:
                        total_cand_score = -999.0
                        break
                    else:
                        total_cand_score += sc

                fallback_score = round((100 - p.join_order) * 0.01, 2)
                if total_cand_score >= 0.0:
                    total_cand_score += fallback_score
                    rule_traces.append(RuleTrace.model_construct(
                        rule_name="FallbackJoinOrder",
                        status="PASS",
                        contribution=fallback_score,
                        details=f"Join order {p.join_order}"
                    ))

                total_cand_score = round(total_cand_score, 2)

                candidate_scores_list.append(CandidateScores.model_construct(
                    participant_id=pid,
                    participant_name=p.display_name,
                    presence_score=scores_by_provider.get("PresenceWindow", 0.0),
                    join_window_score=0.0,
                    dialogue_alternation_score=scores_by_provider.get("ConversationalTransition", 0.0) + scores_by_provider.get("Alternation", 0.0),
                    temporal_continuity_score=scores_by_provider.get("TemporalContinuity", 0.0),
                    vocative_score=scores_by_provider.get("Vocative", 0.0),
                    question_answer_score=0.0,
                    acknowledgement_score=0.0,
                    deepgram_prior_score=scores_by_provider.get("DeepgramPrior", 0.0),
                    fallback_score=fallback_score,
                    final_score=total_cand_score,
                    rule_traces=rule_traces,
                ))

            # Sort candidates by score
            sorted_candidates = sorted(candidate_scores_list, key=lambda c: c.final_score, reverse=True)
            top_candidate = sorted_candidates[0]
            max_score = top_candidate.final_score
            runner_up_score = sorted_candidates[1].final_score if len(sorted_candidates) > 1 else 0.0

            # Apply Confidence Stabilizer Hysteresis
            winner_pid: Optional[str] = None
            winner_pname: Optional[str] = None
            win_reason = "conversation_state"

            if max_score < 0.0 and seg.speaker_label and seg.speaker_label in static_map:
                winner_pid, winner_pname, map_conf = static_map[seg.speaker_label]
                win_reason = "deepgram_prior"
                calc_confidence = map_conf
                winning_traces = []
            elif max_score < 0.0:
                winner_pid = None
                winner_pname = None
                win_reason = "fallback_join_order"
                calc_confidence = 0.0
                winning_traces = []
            else:
                # Check hysteresis threshold against currently active speaker
                curr_active_id = state.current_active_speaker
                curr_active_cand = next((c for c in candidate_scores_list if c.participant_id == curr_active_id), None)

                if (
                    curr_active_cand
                    and curr_active_cand.final_score >= 0.0
                    and top_candidate.participant_id != curr_active_id
                    and (max_score - curr_active_cand.final_score) < _SWITCH_HYSTERESIS_MARGIN
                ):
                    # Maintain current active speaker due to hysteresis threshold
                    winner_candidate = curr_active_cand
                    win_reason = "temporal_continuity"
                else:
                    winner_candidate = top_candidate

                winner_pid = winner_candidate.participant_id
                winner_pname = winner_candidate.participant_name
                winning_traces = winner_candidate.rule_traces

                # Determine primary resolution reason from winning provider trace
                highest_trace = max(
                    [t for t in winning_traces if t.rule_name != "PresenceWindow" and t.rule_name != "FallbackJoinOrder"],
                    key=lambda t: t.contribution,
                    default=None
                )
                if highest_trace and highest_trace.contribution > 0:
                    raw_r = highest_trace.rule_name.lower()
                    if raw_r == "vocative":
                        win_reason = "vocative_detection"
                    elif raw_r in ("conversationaltransition", "alternation", "segmentation"):
                        win_reason = "dialogue_alternation"
                    elif raw_r == "temporalcontinuity":
                        win_reason = "temporal_continuity"
                    elif raw_r == "deepgramprior":
                        win_reason = "deepgram_prior"
                    elif raw_r == "interruption":
                        win_reason = "interruption_recovery"
                    elif raw_r == "ownership":
                        win_reason = "ownership_momentum"
                    else:
                        win_reason = raw_r
                else:
                    win_reason = "fallback_join_order"

                margin = max_score - runner_up_score
                if margin > 10.0:
                    calc_confidence = 0.95
                elif margin > 5.0:
                    calc_confidence = 0.85
                elif margin > 0.0:
                    calc_confidence = 0.70
                else:
                    calc_confidence = 0.50

            score_gap = round(max_score - runner_up_score, 2) if max_score >= 0.0 else 0.0
            total_confidence += calc_confidence
            total_gap += score_gap

            # Update decision counts for statistics
            if win_reason == "fallback_join_order":
                fallback_count += 1
            elif win_reason == "deepgram_prior":
                deepgram_count += 1
            elif win_reason in ("dialogue_alternation", "interruption_recovery", "ownership_momentum"):
                dialogue_count += 1
            elif win_reason == "vocative_detection":
                vocative_count += 1
            elif win_reason == "temporal_continuity":
                continuity_count += 1

            if seg.text.strip().endswith("?"):
                question_count += 1

            # Console diagnostics when DEBUG_ATTRIBUTION=True
            if meeting_config.DEBUG_ATTRIBUTION:
                print(f"\n--- Segment {seg.segment_id} [{seg.start_time:.1f}s - {seg.end_time:.1f}s] ---")
                print(f"Text: \"{seg.text}\" | Deepgram Label: {seg.speaker_label}")
                print("Candidates:")
                for c in candidate_scores_list:
                    print(f"  {c.participant_name} ({c.participant_id}): Final {c.final_score:.2f}")
                print(f"Winner: {winner_pname} ({winner_pid}) | Reason: {win_reason} | Gap: {score_gap:.2f} | Conf: {calc_confidence:.2f}")

            # Detect vocative targets from CandidateScores list for addressee priming in next turn
            vocative_trace = next((t for c in candidate_scores_list for t in c.rule_traces if t.rule_name == "Vocative" and t.contribution < 0), None)
            next_responder = None
            if vocative_trace:
                # Target was identified as addressee with penalty
                bad_pid = next((c.participant_id for c in candidate_scores_list for t in c.rule_traces if t == vocative_trace), None)
                if bad_pid:
                    next_responder = bad_pid

            # Check if winner represents an interruption
            is_interruption = False
            if state.current_active_speaker and winner_pid and winner_pid != state.current_active_speaker:
                gap = max(0.0, seg.start_time - state.last_segment_end_time)
                if gap < 0.5 and seg.end_time - seg.start_time < 2.0:
                    # In diarized meetings, check if the next segment belongs to the same winner
                    is_continuation = False
                    if has_multiple_speakers and idx + 1 < len(attributed_segments):
                        next_seg = attributed_segments[idx + 1]
                        if next_seg.speaker_label and static_map:
                            next_owner = static_map.get(next_seg.speaker_label, (None, None, 0.0))[0]
                            if next_owner == winner_pid:
                                is_continuation = True
                    
                    if not is_continuation:
                        is_interruption = True

            # Advance ConversationState
            state = state.transition(
                winner_pid=winner_pid,
                start_time=seg.start_time,
                end_time=seg.end_time,
                is_interruption=is_interruption,
                next_expected_responder=next_responder,
            )

            meta = dict(seg.metadata)
            meta["attribution_scores"] = {c.participant_id: c.final_score for c in candidate_scores_list}

            resolved_segments.append(
                ParticipantAttributedSegment.model_construct(
                    segment_id=seg.segment_id,
                    raw_segment_id=seg.raw_segment_id,
                    source_stage="resolution",
                    processing_history=[*seg.processing_history, "conversation_state_attribution"],
                    start_time=seg.start_time,
                    end_time=seg.end_time,
                    text=seg.text,
                    speaker_label=seg.speaker_label,
                    speaker_label_confidence=seg.diarization_confidence,
                    participant_id=winner_pid,
                    participant_name=winner_pname,
                    mapping_confidence=round(calc_confidence, 2),
                    confidence=seg.confidence,
                    language=seg.language,
                    resolution_reason=win_reason,
                    metadata=meta,
                )
            )

            decisions.append(
                AttributionDecision.model_construct(
                    segment_id=seg.segment_id,
                    deepgram_label=seg.speaker_label,
                    start_time=seg.start_time,
                    end_time=seg.end_time,
                    text=seg.text,
                    candidate_participants=candidate_scores_list,
                    winner_id=winner_pid,
                    winner_name=winner_pname,
                    winner_score=max_score if max_score >= 0.0 else 0.0,
                    runner_up_score=runner_up_score if runner_up_score >= 0.0 else 0.0,
                    score_gap=score_gap,
                    confidence=round(calc_confidence, 2),
                    resolution_reason=win_reason,
                    decision_trace=winning_traces,
                )
            )

            timeline_items.append(
                AttributionTimelineItem.model_construct(
                    segment_id=seg.segment_id,
                    start_time=seg.start_time,
                    end_time=seg.end_time,
                    text=seg.text,
                    deepgram_label=seg.speaker_label,
                    winner_id=winner_pid,
                    winner_name=winner_pname,
                    resolution_reason=win_reason,
                    confidence=round(calc_confidence, 2),
                )
            )

        duration_ms = int((time.monotonic() - t0) * 1000)
        total_segs = len(resolved_segments)
        avg_conf = round(total_confidence / total_segs, 4) if total_segs > 0 else 0.0
        avg_gap = round(total_gap / total_segs, 4) if total_segs > 0 else 0.0

        stats = AttributionStatistics(
            total_segments=total_segs,
            fallback_decisions=fallback_count,
            deepgram_decisions=deepgram_count,
            dialogue_decisions=dialogue_count,
            vocative_decisions=vocative_count,
            question_decisions=question_count,
            acknowledgement_decisions=acknowledgement_count,
            continuity_decisions=continuity_count,
            average_confidence=avg_conf,
            average_candidate_gap=avg_gap,
        )

        debug_artifact = AttributionDebugArtifact.model_construct(
            meeting_id=meeting_id,
            parent_speaker_attributed_transcript_id=parent_transcript_id,
            statistics=stats,
            decisions=decisions,
            created_at=now_iso,
        )

        timeline_artifact = AttributionTimelineArtifact.model_construct(
            meeting_id=meeting_id,
            parent_speaker_attributed_transcript_id=parent_transcript_id,
            timeline=timeline_items,
            created_at=now_iso,
        )

        log.info(
            "attribution.state_engine.completed",
            segment_count=total_segs,
            average_confidence=avg_conf,
            average_gap=avg_gap,
            duration_ms=duration_ms,
        )
        return resolved_segments, debug_artifact, timeline_artifact
