"""Dynamic Speaker Attribution Engine (Phase 2.5).

Production-grade, deterministic, O(n) local attribution engine with
full observability and explainability trace generation.
No LLM. No AI. No external APIs. No network calls. No statistical models.

Performs per-segment participant identity resolution using weighted evidence signals:
  1. Presence overlap & join/leave windows (hard disqualification)
  2. Vocative detection ("Hey Shivam" -> speaker is NOT Shivam)
  3. Weighted Q&A & dialogue alternation
  4. Weighted short acknowledgement detection
  5. Consecutive turn heuristic
  6. Deepgram speaker label prior (weak prior)
  7. Temporal continuity
  8. Join-order fallback (absolute last resort)
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set, Tuple

from app.meeting.artifacts.speaker import (
    SpeakerAttributedSegment,
    ParticipantAttributedSegment,
    ParticipantAttributedTranscript,
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
from app.meeting.config import meeting_config
from app.meeting.logger import get_logger

log = get_logger("attribution.dynamic_engine")

# Sentence punctuation regex
_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.?!।])\s+")

# Short acknowledgement phrases (case-insensitive)
_ACKNOWLEDGEMENTS: Set[str] = {
    "yes", "okay", "sure", "exactly", "right", "no", "hmm", "hm", "yeah", "yep", "nope",
    "got it", "thanks", "thank you", "yes sir", "no sir", "fine", "understood", "true",
    "i know", "ok", "haan", "thik hai", "sahi", "thik ache", "dhanyabad", "dhanyavaad",
    "have a good day", "bye", "goodbye", "see you", "correct", "of course"
}

# Question prefix words
_QUESTION_WORDS: Set[str] = {
    "how", "what", "why", "who", "where", "when", "can", "could", "would", "should",
    "is", "are", "do", "does", "did", "kyun", "kya", "kaise", "kahan", "keeno", "kine"
}

# Common greeting words
_GREETING_WORDS: Set[str] = {
    "hey", "hello", "hi", "good morning", "good afternoon", "good evening", "welcome"
}

# Command prefix words
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
    if clean in _ACKNOWLEDGEMENTS:
        return True
    words = clean.split()
    return len(words) <= 3 and clean in _ACKNOWLEDGEMENTS


def _extract_first_name(display_name: str) -> str:
    """Extract clean first name for vocative detection."""
    clean = re.sub(r"[^\w\s]", "", display_name.strip())
    parts = clean.split()
    return parts[0].strip() if parts else display_name.strip()


def _detect_vocative_targets(text: str, participants: List[MeetingParticipant]) -> Set[str]:
    clean_text = text.lower()
    targeted_pids: Set[str] = set()

    for p in participants:
        first_name = _extract_first_name(p.display_name).lower()
        if len(first_name) < 2:
            continue

        pattern = r"\b(" + "|".join(_GREETING_WORDS) + r")?\s*" + re.escape(first_name) + r"[\s,\.!\?]|\b" + re.escape(first_name) + r"[\s,\.!\?]"
        if re.search(pattern, clean_text):
            targeted_pids.add(p.participant_id)

    return targeted_pids


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
    """O(n) Deterministic per-turn speaker attribution engine with observability."""

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
            log.warning("attribution.dynamic_engine.empty_roster")
            resolved = [
                ParticipantAttributedSegment(
                    segment_id=seg.segment_id,
                    raw_segment_id=seg.raw_segment_id,
                    source_stage="resolution",
                    processing_history=[*seg.processing_history, "dynamic_attribution"],
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

        # Build presence intervals
        presence_intervals = _build_presence_intervals(participants, presence_timeline)

        # Build fast lookup for Deepgram static mapping prior (if present)
        static_map: Dict[str, Tuple[str, str, float]] = {}
        if mapping:
            for entry in mapping.entries:
                if entry.speaker_label and entry.participant_id:
                    static_map[entry.speaker_label] = (
                        entry.participant_id,
                        entry.participant_name or "",
                        entry.mapping_confidence,
                    )

        # Build participant fast map
        p_by_id: Dict[str, MeetingParticipant] = {p.participant_id: p for p in participants}

        resolved_segments: List[ParticipantAttributedSegment] = []
        decisions: List[AttributionDecision] = []
        timeline_items: List[AttributionTimelineItem] = []

        # Decision category counts for statistics
        fallback_count = 0
        deepgram_count = 0
        dialogue_count = 0
        vocative_count = 0
        question_count = 0
        acknowledgement_count = 0
        continuity_count = 0
        total_confidence = 0.0
        total_gap = 0.0

        prev_participant_id: Optional[str] = None
        prev_text: Optional[str] = None
        prev_vocative_targets: Set[str] = set()
        consecutive_turns: int = 0

        for idx, seg in enumerate(attributed_segments):
            seg_dur = seg.end_time - seg.start_time
            candidate_switch = seg.metadata.get("candidate_speaker_switch", False)
            vocative_targets = _detect_vocative_targets(seg.text, participants)

            candidate_scores_list: List[CandidateScores] = []
            reasons: Dict[str, str] = {}

            for p in participants:
                pid = p.participant_id
                primary_reason = "fallback_join_order"
                rule_traces: List[RuleTrace] = []

                # Component scores
                presence_score = 0.0
                join_window_score = 0.0
                vocative_score = 0.0
                qa_score = 0.0
                dialogue_score = 0.0
                ack_score = 0.0
                continuity_score = 0.0
                deepgram_prior_score = 0.0

                # -----------------------------------------------------------
                # Signal 1: Presence Window Check (Hard Filter)
                # -----------------------------------------------------------
                join_sec, leave_sec = presence_intervals.get(pid, (0.0, float("inf")))
                if seg.start_time < (join_sec - 2.0) or seg.end_time > (leave_sec + 2.0):
                    presence_score = -999.0
                    rule_traces.append(RuleTrace(
                        rule_name="PresenceWindow",
                        status="FAIL",
                        contribution=-999.0,
                        details=f"Outside presence window [{join_sec:.1f}s, {leave_sec:.1f}s]"
                    ))
                else:
                    presence_score = 1.0
                    rule_traces.append(RuleTrace(
                        rule_name="PresenceWindow",
                        status="PASS",
                        contribution=1.0,
                        details=f"Inside presence window [{join_sec:.1f}s, {leave_sec:.1f}s]"
                    ))

                # If disqualified by presence window, skip further positive scoring
                if presence_score < 0.0:
                    fallback_score = round((100 - p.join_order) * 0.01, 2)
                    final_score = -999.0
                    reasons[pid] = "absent_during_timestamp"
                    candidate_scores_list.append(CandidateScores(
                        participant_id=pid,
                        participant_name=p.display_name,
                        presence_score=presence_score,
                        join_window_score=join_window_score,
                        dialogue_alternation_score=0.0,
                        temporal_continuity_score=0.0,
                        vocative_score=0.0,
                        question_answer_score=0.0,
                        acknowledgement_score=0.0,
                        deepgram_prior_score=0.0,
                        fallback_score=fallback_score,
                        final_score=final_score,
                        rule_traces=rule_traces,
                    ))
                    continue

                # -----------------------------------------------------------
                # Signal 2: Vocative Detection & Addressee Priming
                # -----------------------------------------------------------
                if vocative_targets:
                    if pid in vocative_targets:
                        vocative_score -= 25.0
                        rule_traces.append(RuleTrace(
                            rule_name="Vocative",
                            status="FAIL",
                            contribution=-25.0,
                            details="Addressee target in text"
                        ))
                    else:
                        vocative_score += 15.0
                        primary_reason = "vocative_detection"
                        rule_traces.append(RuleTrace(
                            rule_name="Vocative",
                            status="PASS",
                            contribution=15.0,
                            details="Active participant during vocative"
                        ))

                if prev_vocative_targets and pid in prev_vocative_targets:
                    vocative_score += 20.0
                    if primary_reason == "fallback_join_order":
                        primary_reason = "vocative_detection"
                    rule_traces.append(RuleTrace(
                        rule_name="AddresseePriming",
                        status="PASS",
                        contribution=20.0,
                        details="Addressed in previous turn"
                    ))

                # -----------------------------------------------------------
                # Signal 3: Weighted Q&A & Dialogue Alternation
                # -----------------------------------------------------------
                if prev_text:
                    if _is_question(prev_text):
                        if pid != prev_participant_id:
                            qa_score += 15.0
                            if primary_reason == "fallback_join_order":
                                primary_reason = "dialogue_alternation"
                            rule_traces.append(RuleTrace(
                                rule_name="QuestionAnswer",
                                status="PASS",
                                contribution=15.0,
                                details="Answer to previous question"
                            ))
                        else:
                            rule_traces.append(RuleTrace(
                                rule_name="QuestionAnswer",
                                status="FAIL",
                                contribution=0.0,
                                details="Same speaker after question"
                            ))
                    elif _is_acknowledgement(prev_text):
                        if pid != prev_participant_id and (candidate_switch or _is_command(seg.text)):
                            dialogue_score += 15.0
                            if primary_reason == "fallback_join_order":
                                primary_reason = "dialogue_alternation"
                            rule_traces.append(RuleTrace(
                                rule_name="DialogueAlternation",
                                status="PASS",
                                contribution=15.0,
                                details="Switch after acknowledgement"
                            ))

                # -----------------------------------------------------------
                # Signal 4: Weighted Short Acknowledgements
                # -----------------------------------------------------------
                if _is_acknowledgement(seg.text):
                    if prev_participant_id and pid != prev_participant_id:
                        ack_boost = 12.0
                        if candidate_switch:
                            ack_boost += 5.0
                        if prev_text and _is_question(prev_text):
                            ack_boost += 5.0
                        ack_score += ack_boost
                        if primary_reason == "fallback_join_order":
                            primary_reason = "acknowledgement"
                        rule_traces.append(RuleTrace(
                            rule_name="Acknowledgement",
                            status="PASS",
                            contribution=ack_boost,
                            details="Short acknowledgement by opposite participant"
                        ))

                # -----------------------------------------------------------
                # Signal 5 & 6: Consecutive Turn & Temporal Continuity
                # -----------------------------------------------------------
                if prev_participant_id and pid == prev_participant_id:
                    cont_boost = 10.0
                    if candidate_switch:
                        cont_boost = 2.0
                    if consecutive_turns > 5 and candidate_switch:
                        cont_boost -= 6.0
                    elif consecutive_turns > 15:
                        cont_boost -= 12.0
                    continuity_score += cont_boost
                    if primary_reason == "fallback_join_order":
                        primary_reason = "temporal_continuity"
                    rule_traces.append(RuleTrace(
                        rule_name="TemporalContinuity",
                        status="PASS",
                        contribution=cont_boost,
                        details=f"Consecutive turns: {consecutive_turns}"
                    ))
                else:
                    rule_traces.append(RuleTrace(
                        rule_name="TemporalContinuity",
                        status="FAIL",
                        contribution=0.0,
                        details="Speaker switch"
                    ))

                # -----------------------------------------------------------
                # Signal 7: Deepgram Speaker Label Prior (Weak Prior)
                # -----------------------------------------------------------
                if seg.speaker_label and seg.speaker_label in static_map:
                    mapped_pid, _, map_conf = static_map[seg.speaker_label]
                    if pid == mapped_pid:
                        deepgram_prior_score += 4.0
                        if primary_reason == "fallback_join_order":
                            primary_reason = "deepgram_prior"
                        rule_traces.append(RuleTrace(
                            rule_name="DeepgramPrior",
                            status="PASS",
                            contribution=4.0,
                            details=f"Matched Deepgram label {seg.speaker_label}"
                        ))

                # -----------------------------------------------------------
                # Signal 8: Join-Order Baseline Fallback
                # -----------------------------------------------------------
                fallback_score = round((100 - p.join_order) * 0.01, 2)
                rule_traces.append(RuleTrace(
                    rule_name="FallbackJoinOrder",
                    status="PASS",
                    contribution=fallback_score,
                    details=f"Join order {p.join_order}"
                ))

                final_score = round(
                    presence_score + join_window_score + vocative_score + qa_score
                    + dialogue_score + ack_score + continuity_score + deepgram_prior_score + fallback_score,
                    2
                )
                reasons[pid] = primary_reason

                candidate_scores_list.append(CandidateScores(
                    participant_id=pid,
                    participant_name=p.display_name,
                    presence_score=presence_score,
                    join_window_score=join_window_score,
                    dialogue_alternation_score=dialogue_score,
                    temporal_continuity_score=continuity_score,
                    vocative_score=vocative_score,
                    question_answer_score=qa_score,
                    acknowledgement_score=ack_score,
                    deepgram_prior_score=deepgram_prior_score,
                    fallback_score=fallback_score,
                    final_score=final_score,
                    rule_traces=rule_traces,
                ))

            # Pick highest scoring candidate
            sorted_candidates = sorted(candidate_scores_list, key=lambda c: c.final_score, reverse=True)
            winner_candidate = sorted_candidates[0]
            max_score = winner_candidate.final_score
            runner_up_score = sorted_candidates[1].final_score if len(sorted_candidates) > 1 else 0.0

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
                winner_pid = winner_candidate.participant_id
                winner_pname = winner_candidate.participant_name
                win_reason = reasons[winner_pid]
                winning_traces = winner_candidate.rule_traces

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

            # Tally statistics counts
            if win_reason == "fallback_join_order":
                fallback_count += 1
            elif win_reason == "deepgram_prior":
                deepgram_count += 1
            elif win_reason == "dialogue_alternation":
                dialogue_count += 1
            elif win_reason == "vocative_detection":
                vocative_count += 1
            elif win_reason == "acknowledgement":
                acknowledgement_count += 1
            elif win_reason == "temporal_continuity":
                continuity_count += 1

            if prev_text and _is_question(prev_text):
                question_count += 1

            # Console Diagnostics (when DEBUG_ATTRIBUTION=True)
            if meeting_config.DEBUG_ATTRIBUTION:
                log.info(
                    "attribution.debug.segment",
                    segment_id=seg.segment_id,
                    start_time=seg.start_time,
                    end_time=seg.end_time,
                    text=seg.text,
                    deepgram_label=seg.speaker_label,
                    winner=winner_pname,
                    reason=win_reason,
                    gap=score_gap,
                    confidence=calc_confidence,
                )
                print(f"\n--- Segment {seg.segment_id} [{seg.start_time:.1f}s - {seg.end_time:.1f}s] ---")
                print(f"Text: \"{seg.text}\" | Deepgram Label: {seg.speaker_label}")
                print("Candidates:")
                for c in candidate_scores_list:
                    print(f"  {c.participant_name} ({c.participant_id}): Presence {c.presence_score:.1f}, Continuity {c.temporal_continuity_score:.1f}, Vocative {c.vocative_score:.1f}, Q&A {c.question_answer_score:.1f}, Dialogue {c.dialogue_alternation_score:.1f}, Ack {c.acknowledgement_score:.1f}, Deepgram {c.deepgram_prior_score:.1f}, Fallback {c.fallback_score:.2f} -> Total {c.final_score:.2f}")
                print(f"Winner: {winner_pname} ({winner_pid}) | Reason: {win_reason} | Gap: {score_gap:.2f} | Conf: {calc_confidence:.2f}")

            # Update tracking for temporal continuity
            if winner_pid == prev_participant_id:
                consecutive_turns += 1
            else:
                consecutive_turns = 1
                prev_participant_id = winner_pid

            prev_text = seg.text
            prev_vocative_targets = vocative_targets

            meta = dict(seg.metadata)
            meta["attribution_scores"] = {c.participant_id: c.final_score for c in candidate_scores_list}

            resolved_segments.append(
                ParticipantAttributedSegment(
                    segment_id=seg.segment_id,
                    raw_segment_id=seg.raw_segment_id,
                    source_stage="resolution",
                    processing_history=[*seg.processing_history, "dynamic_attribution"],
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
                AttributionDecision(
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
                AttributionTimelineItem(
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

        debug_artifact = AttributionDebugArtifact(
            meeting_id=meeting_id,
            parent_speaker_attributed_transcript_id=parent_transcript_id,
            statistics=stats,
            decisions=decisions,
            created_at=now_iso,
        )

        timeline_artifact = AttributionTimelineArtifact(
            meeting_id=meeting_id,
            parent_speaker_attributed_transcript_id=parent_transcript_id,
            timeline=timeline_items,
            created_at=now_iso,
        )

        log.info(
            "attribution.dynamic_engine.completed",
            segment_count=total_segs,
            average_confidence=avg_conf,
            average_gap=avg_gap,
            duration_ms=duration_ms,
        )
        return resolved_segments, debug_artifact, timeline_artifact
