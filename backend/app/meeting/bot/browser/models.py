"""Browser abstraction models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class BrowserSession:
    """A fully loaded Playwright persistent context session.
    
    Contains the active Playwright instance, the loaded browser context,
    and metadata about the session.
    """
    playwright: Any
    context: Any
    profile_path: Path
    extension_loaded: bool
    browser_launch_audit: dict[str, Any] | None = None

