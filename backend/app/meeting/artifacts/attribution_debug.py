"""Attribution Debug and Observability Artifact Models (Phase 2.5)."""

from __future__ import annotations

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from .base import MeetingArtifact


class RuleTrace(BaseModel):
    """Execution trace for a single rule or heuristic on a candidate participant."""
    rule_name: str              # e.g., "PresenceWindow", "Vocative", "QuestionAnswer"
    status: str                 # "PASS" | "FAIL"
    contribution: float         # score delta e.g. +15.0, 0.0, -25.0
    details: Optional[str] = None


class CandidateScores(BaseModel):
    """Exposes all individual score components for one candidate participant."""
    participant_id: str
    participant_name: str
    presence_score: float = 0.0
    join_window_score: float = 0.0
    dialogue_alternation_score: float = 0.0
    temporal_continuity_score: float = 0.0
    vocative_score: float = 0.0
    question_answer_score: float = 0.0
    acknowledgement_score: float = 0.0
    deepgram_prior_score: float = 0.0
    fallback_score: float = 0.0
    final_score: float = 0.0
    rule_traces: List[RuleTrace] = Field(default_factory=list)


class AttributionDecision(BaseModel):
    """Complete explainability record for a single transcript segment attribution decision."""
    segment_id: str
    deepgram_label: Optional[str] = None
    start_time: float
    end_time: float
    text: str
    candidate_participants: List[CandidateScores]
    winner_id: Optional[str] = None
    winner_name: Optional[str] = None
    winner_score: float = 0.0
    runner_up_score: float = 0.0
    score_gap: float = 0.0
    confidence: float = 0.0
    resolution_reason: str
    decision_trace: List[RuleTrace] = Field(default_factory=list)


class AttributionStatistics(BaseModel):
    """Aggregate statistics summarizing attribution decisions across a meeting session."""
    total_segments: int = 0
    fallback_decisions: int = 0
    deepgram_decisions: int = 0
    dialogue_decisions: int = 0
    vocative_decisions: int = 0
    question_decisions: int = 0
    acknowledgement_decisions: int = 0
    continuity_decisions: int = 0
    average_confidence: float = 0.0
    average_candidate_gap: float = 0.0


class AttributionTimelineItem(BaseModel):
    """Lightweight timeline entry for quick visual inspection of speaker sequence."""
    segment_id: str
    start_time: float
    end_time: float
    text: str
    deepgram_label: Optional[str] = None
    winner_id: Optional[str] = None
    winner_name: Optional[str] = None
    resolution_reason: str
    confidence: float = 0.0


class AttributionDebugArtifact(MeetingArtifact):
    """Detailed debug artifact for meeting attribution decisions (attribution_debug.json)."""
    parent_speaker_attributed_transcript_id: str
    statistics: AttributionStatistics
    decisions: List[AttributionDecision]
    created_at: str
    processing_version: str = "1.0.0"


class AttributionTimelineArtifact(MeetingArtifact):
    """Timeline summary artifact of resolved meeting participants (attribution_timeline.json)."""
    parent_speaker_attributed_transcript_id: str
    timeline: List[AttributionTimelineItem]
    created_at: str
    processing_version: str = "1.0.0"
