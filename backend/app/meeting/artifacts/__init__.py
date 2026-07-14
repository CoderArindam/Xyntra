# Expose artifacts
from .base import MeetingArtifact
from .recording import MeetingRecording, AudioSegment, ProcessedAudio
from .transcript import (
    TranscriptSegment,
    SpeakerSegment,
    RawTranscript,
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
    "NormalizedTranscript",
    "MeetingTranscript",
    "MeetingInsights",
    "DecisionItem",
    "ActionItem",
    "ExtractedTask",
    "TaskProposal",
]
