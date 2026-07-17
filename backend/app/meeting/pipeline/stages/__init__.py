"""Pipeline stages package."""

from .preprocessing import AudioPreprocessingStage
from .speech_processing import SpeechProcessingStage
from .normalization import TranscriptNormalizationStage
from .segmentation import ConversationSegmentationStage
from .alignment import SpeakerAlignmentStage
from .presence import PresenceCollectionStage
from .roster import ParticipantRosterStage
from .mapping import SpeakerMappingStage
from .resolution import ParticipantResolutionStage

# Default order of execution.
# Can also be constructed dynamically by sorting on stage.execution_order
ALL_STAGES = [
    AudioPreprocessingStage(),        # order 100 — audio normalization
    SpeechProcessingStage(),          # order 200 — STT + diarization (Deepgram)
    TranscriptNormalizationStage(),   # order 300 — text cleaning
    ConversationSegmentationStage(),  # order 400 — turn segmentation
    SpeakerAlignmentStage(),          # order 500 — turn → segment alignment
    PresenceCollectionStage(),        # order 600 — participant presence
    ParticipantRosterStage(),         # order 700 — roster building
    SpeakerMappingStage(),            # order 800 — speaker → participant mapping
    ParticipantResolutionStage(),     # order 900 — final attribution
]
