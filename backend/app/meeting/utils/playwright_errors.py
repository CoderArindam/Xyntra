"""Centralized Playwright exception detection.

All observer loops, the heartbeat monitor, and cleanup helpers import from
here.  No other file should inspect Playwright exception strings directly.
"""

from __future__ import annotations
from typing import Any


def _get_playwright_error_types() -> tuple[type, ...]:
    """Lazy-import Playwright error classes; return empty tuple if missing."""
    types: list[type] = []
    try:
        from playwright._impl._errors import TargetClosedError  # type: ignore
        types.append(TargetClosedError)
    except ImportError:
        pass
    try:
        from playwright._impl._errors import Error as PwError  # type: ignore
        types.append(PwError)
    except ImportError:
        pass
    return tuple(types)


def is_target_closed(exc: BaseException) -> bool:
    """True when Playwright signals page/context/browser was closed."""
    try:
        from playwright._impl._errors import TargetClosedError  # type: ignore
        if isinstance(exc, TargetClosedError):
            return True
    except ImportError:
        pass
    # Fallback: older Playwright versions surface this as a generic Error
    # with a specific class name that sub-modules may re-export.
    if type(exc).__name__ == "TargetClosedError":
        return True
    return False


def is_browser_disconnected(exc: BaseException) -> bool:
    """True for connection-level disconnects (browser process died)."""
    try:
        from playwright._impl._errors import Error as PwError  # type: ignore
        if (
            isinstance(exc, PwError)
            and "browser has been closed" in str(exc).lower()
        ):
            return True
    except ImportError:
        pass
    if type(exc).__name__ == "BrowserClosedError":
        return True
    return False


def is_playwright_fatal(exc: BaseException) -> bool:
    """True if browser/page is irrecoverably gone."""
    return is_target_closed(exc) or is_browser_disconnected(exc)


def page_is_usable(page: Any) -> bool:
    """Return True only if the page object exists and is not closed."""
    if page is None:
        return False
    try:
        return not page.is_closed()
    except Exception:
        return False
