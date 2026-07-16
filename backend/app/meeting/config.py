"""Meeting module configuration — all settings read from environment.

All env vars use the `MEETING_` prefix. No os.getenv() anywhere else in
the meeting module; import `meeting_config` instead.
"""

from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class MeetingSettings(BaseSettings):
    """Reads MEETING_* environment variables from .env and environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MEETING_",
        extra="ignore",
        env_file_encoding="utf-8",
    )

    # ------------------------------------------------------------------ #
    # Browser                                                              #
    # ------------------------------------------------------------------ #
    HEADLESS: bool = True

    # ------------------------------------------------------------------ #
    # Google credentials                                                   #
    # ------------------------------------------------------------------ #
    GOOGLE_EMAIL: str = ""
    GOOGLE_PASSWORD: str = ""

    # ------------------------------------------------------------------ #
    # Browser profile                                                      #
    # ------------------------------------------------------------------ #
    PROFILE_DIR: str = str(Path("storage") / "meeting" / "profile")

    # ------------------------------------------------------------------ #
    # Bot identity                                                         #
    # ------------------------------------------------------------------ #
    BOT_NAME: str = "KAIO Bot"

    # ------------------------------------------------------------------ #
    # Timeouts & retries                                                   #
    # ------------------------------------------------------------------ #
    JOIN_TIMEOUT: int = 60        # seconds — max time to land in meeting
    PAGE_TIMEOUT: int = 30_000   # ms     — Playwright default timeout
    AUTH_TIMEOUT: int = 45        # seconds — max time for Google auth
    RETRY_COUNT: int = 3
    RETRY_BASE_DELAY: float = 2.0  # seconds
    RETRY_MAX_DELAY: float = 30.0  # seconds

    # ------------------------------------------------------------------ #
    # Health monitor                                                       #
    # ------------------------------------------------------------------ #
    HEARTBEAT_INTERVAL: float = 5.0  # seconds between heartbeat ticks

    # ------------------------------------------------------------------ #
    # Debug & diagnostics                                                  #
    # ------------------------------------------------------------------ #
    DEBUG_DIR: str = str(Path("storage") / "meeting" / "debug")
    SCREENSHOT_ON_FAILURE: bool = True

    # ------------------------------------------------------------------ #
    # Concurrency                                                          #
    # ------------------------------------------------------------------ #
    MAX_CONCURRENT_SESSIONS: int = 3
    MEETING_TIMEOUT: int = 3600  # seconds — max session duration

    # ------------------------------------------------------------------ #
    # Pipeline & Processing                                                #
    # ------------------------------------------------------------------ #
    STT_PROVIDER: str = "whisper"
    STT_MULTILINGUAL_ENABLED: bool = True
    DIARIZATION_PROVIDER: str = "pyannote"
    INTELLIGENCE_PROVIDER: str = "gemini"
    TRANSLATION_PROVIDER: str = ""
    EMBEDDING_PROVIDER: str = ""
    PIPELINE_CHUNK_DURATION_SEC: int = 30
    PIPELINE_MAX_RETRIES: int = 3
    ARTIFACT_RETENTION_DAYS: int = 30

    # ------------------------------------------------------------------ #
    # Recording                                                            #
    # ------------------------------------------------------------------ #
    RECORDING_OUTPUT_DIR: str = str(Path("storage") / "meeting" / "recordings")
    RECORDING_FORMAT: str = "webm"
    RECORDING_SAMPLE_RATE: int = 48000
    RECORDING_MAX_DURATION: int = 14400      # seconds — 4 hours hard cap
    RECORDING_BUFFER_SIZE: int = 10_485_760  # bytes  — 10 MB in-memory buffer
    # ------------------------------------------------------------------ #
    # Audio Processing                                                     #
    # ------------------------------------------------------------------ #
    PROCESSING_OUTPUT_DIR: str = str(Path("storage") / "meeting" / "processed_audio")
    CANONICAL_SAMPLE_RATE: int = 16000       # Hz — optimal for STT
    CANONICAL_CHANNELS: int = 1             # mono
    CANONICAL_FORMAT: str = "wav"           # uncompressed for STT fidelity
    MIN_RECORDING_DURATION: float = 1.0     # seconds — reject very short recordings
    MAX_RECORDING_SIZE: int = 2_147_483_648 # bytes — 2 GB
    ENABLE_AUDIO_NORMALIZATION: bool = True
    FFMPEG_PATH: str = "ffmpeg"
    FFPROBE_PATH: str = "ffprobe"
    # ------------------------------------------------------------------ #
    # Speech-to-Text (STT)                                                 #
    # ------------------------------------------------------------------ #
    WHISPER_MODEL: str = "small"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "int8"
    WHISPER_BEAM_SIZE: int = 5
    WHISPER_LANGUAGE: str = ""
    WHISPER_ENABLE_VAD: bool = True
    WHISPER_BATCH_SIZE: int = 8
    # ------------------------------------------------------------------ #
    # Experimental: Groq Speech-to-Text                                    #
    # ------------------------------------------------------------------ #
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "whisper-large-v3"
    GROQ_TIMEOUT: int = 300
    GROQ_MAX_RETRIES: int = 3

    # ------------------------------------------------------------------ #
    # Transcript Normalization                                             #
    # ------------------------------------------------------------------ #
    NORMALIZATION_ENABLE_FILLER_REMOVAL: bool = True
    # Segment merging is intentionally disabled.
    # Transcript boundaries are produced by the STT provider and must remain
    # immutable through the normalization stage. If future UI formatting
    # requires merged paragraphs, that must happen in a separate rendering
    # layer after speaker attribution is complete.
    NORMALIZATION_ENABLE_SEGMENT_MERGE: bool = False
    NORMALIZATION_ENABLE_DUPLICATE_REMOVAL: bool = True
    NORMALIZATION_ENABLE_CAPITALIZATION: bool = True
    NORMALIZATION_ENABLE_PUNCTUATION: bool = True
    # Repeated-char rule is disabled by default — language-specific dicts
    # required for safe correction (e.g. "committee" must not collapse).
    NORMALIZATION_ENABLE_REPEATED_CHARS: bool = False
    # Max silence gap (ms) between adjacent segments eligible for merging
    NORMALIZATION_MAX_SEGMENT_GAP_MS: int = 1500
    # Max combined character length for a merged segment
    NORMALIZATION_MAX_SEGMENT_LENGTH: int = 500
    NORMALIZATION_PROCESSING_VERSION: str = "1.0.0"

    # ------------------------------------------------------------------ #
    # Speaker Diarization (Pyannote)                                       #
    # ------------------------------------------------------------------ #
    DIARIZATION_PYANNOTE_AUTH_TOKEN: str = ""
    DIARIZATION_PYANNOTE_MODEL: str = "pyannote/speaker-diarization-3.1"
    DIARIZATION_MIN_SPEAKERS: int = 1
    DIARIZATION_MAX_SPEAKERS: int = 10
    DIARIZATION_PROCESSING_VERSION: str = "1.0.0"

    # ------------------------------------------------------------------ #
    # Speaker Attribution                                                  #
    # ------------------------------------------------------------------ #
    # Minimum segment-to-turn overlap ratio required to assign a speaker label.
    # A value of 0.5 means the turn must cover ≥50% of the segment's duration.
    ATTRIBUTION_OVERLAP_THRESHOLD: float = 0.5
    ATTRIBUTION_PROCESSING_VERSION: str = "1.0.0"

    # ------------------------------------------------------------------ #
    # Speaker Alignment (M2.6.1)                                         #
    # ------------------------------------------------------------------ #
    # Minimum segment-to-turn overlap ratio required to assign a speaker label.
    ALIGNMENT_OVERLAP_THRESHOLD: float = 0.5
    ALIGNMENT_SCORE_SEGMENT_WEIGHT: float = 0.70
    ALIGNMENT_SCORE_SPEAKER_WEIGHT: float = 0.30
    ALIGNMENT_MIN_TURN_DURATION_MS: int = 200
    ALIGNMENT_MERGE_GAP_MS: int = 250
    ALIGNMENT_PROCESSING_VERSION: str = "1.1.0"

    # ------------------------------------------------------------------ #
    # Speaker Mapping (M2.7)                                             #
    # ------------------------------------------------------------------ #
    PARTICIPANT_PROVIDER: str = "external"  # "json" | "google" | "external"
    MAPPING_STRATEGY: str = "join_order"
    MAPPING_PROCESSING_VERSION: str = "1.0.0"

    # ------------------------------------------------------------------ #
    # Chrome Extension (M2.7.8)                                          #
    # ------------------------------------------------------------------ #
    EXTENSION_API_KEY_HASH: str = ""
    EXTENSION_ENABLED: bool = True
    EXTENSION_DIRECTORY: str = "../extension"

meeting_config = MeetingSettings()
