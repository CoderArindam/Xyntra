"""Pipeline stages package."""

from .preprocessing import AudioPreprocessingStage
from .transcription import SpeechRecognitionStage
from .normalization import TranscriptNormalizationStage
from .diarization import SpeakerDiarizationStage
from .alignment import SpeakerAlignmentStage
from .presence import PresenceCollectionStage
from .roster import ParticipantRosterStage
from .mapping import SpeakerMappingStage
from .resolution import ParticipantResolutionStage

# Default order of execution.
# Can also be constructed dynamically by sorting on stage.execution_order
ALL_STAGES = [
    AudioPreprocessingStage(),
    SpeechRecognitionStage(),
    TranscriptNormalizationStage(),
    SpeakerDiarizationStage(),
    SpeakerAlignmentStage(),
    PresenceCollectionStage(),
    ParticipantRosterStage(),
    SpeakerMappingStage(),
    ParticipantResolutionStage(),
]
