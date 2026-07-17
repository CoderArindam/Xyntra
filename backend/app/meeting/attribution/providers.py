"""Modular Evidence Providers (Phase 2.6).

Independent, deterministic evidence modules evaluating conversation dynamics.
No language-specific keyword dictionaries. Punctuation is treated as a weak secondary hint.
"""

from __future__ import annotations

import re
from typing import List, Dict, Tuple, Optional, Set
from abc import ABC, abstractmethod

from app.meeting.artifacts.speaker import SpeakerAttributedSegment, MeetingParticipant, SpeakerMapping
from app.meeting.artifacts.attribution_debug import RuleTrace
from app.meeting.attribution.conversation_state import ConversationState

# Common greeting words for name extraction
_GREETING_WORDS: Set[str] = {
    "hey", "hello", "hi", "good morning", "good afternoon", "good evening", "welcome"
}


def _extract_first_name(display_name: str) -> str:
    clean = re.sub(r"[^\w\s]", "", display_name.strip())
    parts = clean.split()
    return parts[0].strip() if parts else display_name.strip()


def _detect_vocative_targets(text: str, participants: List[MeetingParticipant]) -> Set[str]:
    clean_text = text.lower()
    if not any(w in clean_text for w in (",", "?", "!", "hey", "hello", "hi")):
        return set()

    targeted_pids: Set[str] = set()
    for p in participants:
        first_name = _extract_first_name(p.display_name).lower()
        if len(first_name) < 2 or first_name not in clean_text:
            continue

        pattern = r"\b(" + "|".join(_GREETING_WORDS) + r")\s+" + re.escape(first_name) + r"\b|\b" + re.escape(first_name) + r"\s*[,!?]"
        if re.search(pattern, clean_text):
            targeted_pids.add(p.participant_id)

    return targeted_pids


class EvidenceProvider(ABC):
    """Abstract base class for deterministic evidence providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    def evaluate(
        self,
        segment: SpeakerAttributedSegment,
        participant: MeetingParticipant,
        state: ConversationState,
        presence_window: Tuple[float, float],
        static_map: Dict[str, Tuple[str, str, float]],
        all_participants: List[MeetingParticipant],
    ) -> Tuple[float, RuleTrace]:
        """Return (score_contribution, rule_trace)."""
        pass


class PresenceEvidenceProvider(EvidenceProvider):
    """Rejects participants absent during the segment timestamp window."""

    @property
    def provider_name(self) -> str:
        return "PresenceWindow"

    def evaluate(
        self,
        segment: SpeakerAttributedSegment,
        participant: MeetingParticipant,
        state: ConversationState,
        presence_window: Tuple[float, float],
        static_map: Dict[str, Tuple[str, str, float]],
        all_participants: List[MeetingParticipant],
    ) -> Tuple[float, RuleTrace]:
        join_sec, leave_sec = presence_window
        if segment.start_time < (join_sec - 2.0) or segment.end_time > (leave_sec + 2.0):
            return -999.0, RuleTrace.model_construct(
                rule_name=self.provider_name,
                status="FAIL",
                contribution=-999.0,
                details=f"Outside presence window [{join_sec:.1f}s, {leave_sec:.1f}s]"
            )
        return 1.0, RuleTrace.model_construct(
            rule_name=self.provider_name,
            status="PASS",
            contribution=1.0,
            details=f"Inside presence window [{join_sec:.1f}s, {leave_sec:.1f}s]"
        )


class VocativeEvidenceProvider(EvidenceProvider):
    """Detects direct name address (addressee penalty + non-addressee boost + addressee priming)."""

    @property
    def provider_name(self) -> str:
        return "Vocative"

    def evaluate(
        self,
        segment: SpeakerAttributedSegment,
        participant: MeetingParticipant,
        state: ConversationState,
        presence_window: Tuple[float, float],
        static_map: Dict[str, Tuple[str, str, float]],
        all_participants: List[MeetingParticipant],
    ) -> Tuple[float, RuleTrace]:
        pid = participant.participant_id
        targets = _detect_vocative_targets(segment.text, all_participants)

        score = 0.0
        details = []

        if targets:
            if pid in targets:
                score -= 25.0
                details.append("Addressee in text (speaker penalty)")
            else:
                score += 15.0
                details.append("Active participant during vocative")

        if state.expected_responder and pid == state.expected_responder:
            score += 20.0
            details.append("Addressed in previous turn (addressee priming)")

        if score != 0.0:
            status = "PASS" if score > 0 else "FAIL"
            return score, RuleTrace.model_construct(
                rule_name=self.provider_name,
                status=status,
                contribution=score,
                details="; ".join(details)
            )

        return 0.0, RuleTrace.model_construct(
            rule_name=self.provider_name,
            status="FAIL",
            contribution=0.0,
            details="No vocative target"
        )


class TemporalContinuityProvider(EvidenceProvider):
    """Weak stabilizer encouraging continuity when no stronger evidence exists."""

    @property
    def provider_name(self) -> str:
        return "TemporalContinuity"

    def evaluate(
        self,
        segment: SpeakerAttributedSegment,
        participant: MeetingParticipant,
        state: ConversationState,
        presence_window: Tuple[float, float],
        static_map: Dict[str, Tuple[str, str, float]],
        all_participants: List[MeetingParticipant],
    ) -> Tuple[float, RuleTrace]:
        pid = participant.participant_id
        candidate_switch = segment.metadata.get("candidate_speaker_switch", False)

        if state.current_active_speaker and pid == state.current_active_speaker:
            score = 2.0 if candidate_switch else 6.0
            if state.consecutive_turns > 5 and candidate_switch:
                score -= 4.0
            elif state.consecutive_turns > 15:
                score -= 8.0
            return score, RuleTrace(
                rule_name=self.provider_name,
                status="PASS",
                contribution=score,
                details=f"Active speaker (consecutive: {state.consecutive_turns})"
            )

        return 0.0, RuleTrace(
            rule_name=self.provider_name,
            status="FAIL",
            contribution=0.0,
            details="Not active speaker"
        )


class ConversationalTransitionProvider(EvidenceProvider):
    """Structural transitions evaluated via timing gaps, pauses, duration, and state."""

    @property
    def provider_name(self) -> str:
        return "ConversationalTransition"

    def evaluate(
        self,
        segment: SpeakerAttributedSegment,
        participant: MeetingParticipant,
        state: ConversationState,
        presence_window: Tuple[float, float],
        static_map: Dict[str, Tuple[str, str, float]],
        all_participants: List[MeetingParticipant],
    ) -> Tuple[float, RuleTrace]:
        pid = participant.participant_id
        dur = segment.end_time - segment.start_time
        gap = max(0.0, segment.start_time - state.last_segment_end_time)
        candidate_switch = segment.metadata.get("candidate_speaker_switch", False)

        score = 0.0
        details = []

        if candidate_switch and state.current_active_speaker and pid != state.current_active_speaker:
            score += 6.0
            details.append("Candidate speaker switch boundary")

        if gap > 1.0 and state.current_active_speaker and pid != state.current_active_speaker:
            score += 4.0
            details.append(f"Pause gap {gap:.1f}s favors transition")

        if dur < 2.0 and state.current_active_speaker and pid != state.current_active_speaker and candidate_switch:
            score += 5.0
            details.append(f"Short duration {dur:.1f}s favors response turn")

        if segment.text.strip().endswith("?") and pid != state.current_active_speaker:
            score += 3.0
            details.append("Punctuation hint (?)")

        if score > 0:
            return score, RuleTrace(
                rule_name=self.provider_name,
                status="PASS",
                contribution=score,
                details="; ".join(details)
            )

        return 0.0, RuleTrace(
            rule_name=self.provider_name,
            status="FAIL",
            contribution=0.0,
            details="No transition features triggered"
        )


class OwnershipProvider(EvidenceProvider):
    """Tracks speaking ownership and gradual momentum decay."""

    @property
    def provider_name(self) -> str:
        return "Ownership"

    def evaluate(
        self,
        segment: SpeakerAttributedSegment,
        participant: MeetingParticipant,
        state: ConversationState,
        presence_window: Tuple[float, float],
        static_map: Dict[str, Tuple[str, str, float]],
        all_participants: List[MeetingParticipant],
    ) -> Tuple[float, RuleTrace]:
        pid = participant.participant_id
        momentum = state.speaker_momentum.get(pid, 0.0)
        is_owner = (state.conversation_ownership == pid)

        score = 0.0
        if is_owner:
            score += 3.0
        score += min(momentum * 1.0, 4.0)

        score = round(score, 2)
        if score > 0:
            return score, RuleTrace(
                rule_name=self.provider_name,
                status="PASS",
                contribution=score,
                details=f"Ownership owner={is_owner}, momentum={momentum:.2f}"
            )

        return 0.0, RuleTrace(
            rule_name=self.provider_name,
            status="FAIL",
            contribution=0.0,
            details="No ownership momentum"
        )


class AlternationProvider(EvidenceProvider):
    """Recognizes natural turn-taking probabilities after completed turns."""

    @property
    def provider_name(self) -> str:
        return "Alternation"

    def evaluate(
        self,
        segment: SpeakerAttributedSegment,
        participant: MeetingParticipant,
        state: ConversationState,
        presence_window: Tuple[float, float],
        static_map: Dict[str, Tuple[str, str, float]],
        all_participants: List[MeetingParticipant],
    ) -> Tuple[float, RuleTrace]:
        pid = participant.participant_id
        candidate_switch = segment.metadata.get("candidate_speaker_switch", False)

        if state.consecutive_turns >= 1 and candidate_switch and pid != state.current_active_speaker:
            score = 10.0
            return score, RuleTrace(
                rule_name=self.provider_name,
                status="PASS",
                contribution=score,
                details=f"Natural turn alternation after {state.consecutive_turns} turns"
            )

        return 0.0, RuleTrace(
            rule_name=self.provider_name,
            status="FAIL",
            contribution=0.0,
            details="No alternation boost"
        )


class InterruptionProvider(EvidenceProvider):
    """Detects A -> B -> A interruptions and awards recovery score when A resumes."""

    @property
    def provider_name(self) -> str:
        return "Interruption"

    def evaluate(
        self,
        segment: SpeakerAttributedSegment,
        participant: MeetingParticipant,
        state: ConversationState,
        presence_window: Tuple[float, float],
        static_map: Dict[str, Tuple[str, str, float]],
        all_participants: List[MeetingParticipant],
    ) -> Tuple[float, RuleTrace]:
        pid = participant.participant_id
        gap = max(0.0, segment.start_time - state.last_segment_end_time)

        if pid in state.interruption_stack and gap < 4.0:
            score = 12.0
            return score, RuleTrace(
                rule_name=self.provider_name,
                status="PASS",
                contribution=score,
                details="Interruption recovery: speaker resumed after brief interruption"
            )

        return 0.0, RuleTrace(
            rule_name=self.provider_name,
            status="FAIL",
            contribution=0.0,
            details="No interruption recovery"
        )


class SegmentationProvider(EvidenceProvider):
    """Consumes metadata produced by Conversation Turn Segmentation."""

    @property
    def provider_name(self) -> str:
        return "Segmentation"

    def evaluate(
        self,
        segment: SpeakerAttributedSegment,
        participant: MeetingParticipant,
        state: ConversationState,
        presence_window: Tuple[float, float],
        static_map: Dict[str, Tuple[str, str, float]],
        all_participants: List[MeetingParticipant],
    ) -> Tuple[float, RuleTrace]:
        pid = participant.participant_id
        candidate_switch = segment.metadata.get("candidate_speaker_switch", False)

        if candidate_switch and pid != state.current_active_speaker:
            score = 5.0
            return score, RuleTrace(
                rule_name=self.provider_name,
                status="PASS",
                contribution=score,
                details="Segmentation candidate_speaker_switch=True"
            )

        return 0.0, RuleTrace(
            rule_name=self.provider_name,
            status="FAIL",
            contribution=0.0,
            details="No segmentation hint"
        )


class DeepgramPriorProvider(EvidenceProvider):
    """Treats Deepgram diarization labels as weak prior information."""

    @property
    def provider_name(self) -> str:
        return "DeepgramPrior"

    def evaluate(
        self,
        segment: SpeakerAttributedSegment,
        participant: MeetingParticipant,
        state: ConversationState,
        presence_window: Tuple[float, float],
        static_map: Dict[str, Tuple[str, str, float]],
        all_participants: List[MeetingParticipant],
    ) -> Tuple[float, RuleTrace]:
        pid = participant.participant_id
        if segment.speaker_label and segment.speaker_label in static_map:
            mapped_pid, _, map_conf = static_map[segment.speaker_label]
            if pid == mapped_pid:
                score = 3.0
                return score, RuleTrace(
                    rule_name=self.provider_name,
                    status="PASS",
                    contribution=score,
                    details=f"Matched Deepgram prior label {segment.speaker_label}"
                )

        return 0.0, RuleTrace(
            rule_name=self.provider_name,
            status="FAIL",
            contribution=0.0,
            details="No Deepgram prior match"
        )
