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


meeting_config = MeetingSettings()
