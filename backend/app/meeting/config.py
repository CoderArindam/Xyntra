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


meeting_config = MeetingSettings()
