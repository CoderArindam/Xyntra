# Expose artifacts
from .base import MeetingArtifact
from .recording import MeetingRecording, AudioSegment, ProcessedAudio
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

__all__ = [
    "MeetingArtifact",
    "MeetingRecording",
    "AudioSegment",
    "ProcessedAudio",
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
]
