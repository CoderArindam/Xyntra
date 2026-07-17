"""Provider-independent internal transcription models.

These are the canonical in-memory representations between the raw provider
SDK response and the pipeline artifact layer. No provider-specific types
ever leak beyond the provider implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TranscriptionWord:
    """A single recognized word with full timing and speaker metadata."""

    text: str
    start: float                        # seconds
    end: float                          # seconds
    confidence: Optional[float] = None
    speaker: Optional[str] = None       # "SPEAKER_0", "SPEAKER_1", …
    speaker_confidence: Optional[float] = None
    punctuated_word: Optional[str] = None


@dataclass
class TranscriptionUtterance:
    """A continuous speech segment attributed to a single speaker."""

    speaker: Optional[str]
    start: float
    end: float
    text: str
    confidence: Optional[float] = None
    words: List[TranscriptionWord] = field(default_factory=list)


@dataclass
class TranscriptionSentence:
    text: str
    start: float
    end: float


@dataclass
class TranscriptionParagraph:
    speaker: Optional[str]
    start: float
    end: float
    text: str
    sentences: List[TranscriptionSentence] = field(default_factory=list)


@dataclass
class TranscriptionResult:
    """Complete, provider-independent transcription result.

    All Deepgram-specific types are converted into this structure inside
    DeepgramSpeechProvider. Nothing downstream ever sees a Deepgram SDK object.
    """

    # Core output
    transcript: str                             # Full concatenated text
    language: str                               # BCP-47 detected language code
    duration: float                             # Audio duration seconds

    # Provider identity — for logging/metrics only
    provider: str                               # "deepgram"
    model: str                                  # "nova-3"

    # Quality
    confidence: Optional[float] = None
    language_confidence: Optional[float] = None

    # Rich structure
    utterances: List[TranscriptionUtterance] = field(default_factory=list)
    paragraphs: List[TranscriptionParagraph] = field(default_factory=list)
    words: List[TranscriptionWord] = field(default_factory=list)

    # Speaker summary
    speakers: List[str] = field(default_factory=list)   # unique speaker labels
    speaker_count: int = 0

    # Raw provider metadata — preserved for debugging/future use, never used in business logic
    raw_metadata: Dict[str, Any] = field(default_factory=dict)
