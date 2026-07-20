# Expose artifacts
from .base import MeetingArtifact
from .recording import MeetingRecording, ProcessedAudio
from .speaker import (
    DiarizationProviderInfo,
    SpeakerTurn,
    MeetingParticipant,
    SpeakerMappingEntry,
    SpeakerAttributedSegment,
    ParticipantAttributedSegment,
    SpeakerTimeline,
    ParticipantRoster,
    SpeakerMapping,
    SpeakerAttributedTranscript,
    ParticipantAttributedTranscript,
)
from .transcript import (
    WordInfo,
    TranscriptSegment,
    SpeakerSegment,
    RawTranscript,
    NormalizedTranscriptSegment,
    NormalizationStatistics,
    NormalizedTranscript,
    MeetingTranscript,
)
from .intelligence import MeetingInsights
from .task import DecisionItem, ActionItem, ExtractedTask, TaskProposal
from .attribution_debug import (
    RuleTrace,
    CandidateScores,
    AttributionDecision,
    AttributionStatistics,
    AttributionTimelineItem,
    AttributionDebugArtifact,
    AttributionTimelineArtifact,
)

__all__ = [
    "MeetingArtifact",
    "MeetingRecording",
    "ProcessedAudio",
    "WordInfo",
    "TranscriptSegment",
    "SpeakerSegment",
    "RawTranscript",
    "NormalizedTranscriptSegment",
    "NormalizationStatistics",
    "NormalizedTranscript",
    "MeetingTranscript",
    "MeetingInsights",
    "DecisionItem",
    "ActionItem",
    "ExtractedTask",
    "TaskProposal",
    # Speaker diarization & attribution
    "DiarizationProviderInfo",
    "SpeakerTurn",
    "MeetingParticipant",
    "SpeakerMappingEntry",
    "SpeakerAttributedSegment",
    "ParticipantAttributedSegment",
    "SpeakerTimeline",
    "ParticipantRoster",
    "SpeakerMapping",
    "SpeakerAttributedTranscript",
    "ParticipantAttributedTranscript",
    # Observability & Debugging
    "RuleTrace",
    "CandidateScores",
    "AttributionDecision",
    "AttributionStatistics",
    "AttributionTimelineItem",
    "AttributionDebugArtifact",
    "AttributionTimelineArtifact",
]

