"""Structured logger factory for the meeting module.

All meeting loggers follow the `meeting.*` namespace and emit structured
context fields (session_id, state, elapsed_ms) alongside the message.

Pipeline stage logging should follow these boundaries:
- `meeting.pipeline.started` / `.completed` / `.failed`
- `meeting.stage.stt.started` / `.completed`
- `meeting.stage.diarization.started` / `.completed`
- `meeting.artifact.generated`
"""

from __future__ import annotations

import logging
import time
from typing import Any


class MeetingLogger:
    """Wraps stdlib logger with structured context support.

    Usage:
        log = get_logger("browser.controller")
        log.info("Browser launched", session_id=sid, elapsed_ms=120)
    """

    def __init__(self, name: str) -> None:
        self._log = logging.getLogger(f"meeting.{name}")
        self._log.setLevel(logging.INFO)
        if not self._log.handlers:
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            self._log.addHandler(ch)
            self._log.propagate = False

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    def _format(self, msg: str, ctx: dict[str, Any]) -> str:
        if not ctx:
            return msg
        fields = " ".join(f"{k}={v}" for k, v in ctx.items() if v is not None)
        return f"{msg} [{fields}]"

    # ------------------------------------------------------------------ #
    # Public                                                               #
    # ------------------------------------------------------------------ #

    def debug(self, msg: str, **ctx: Any) -> None:
        self._log.debug(self._format(msg, ctx))

    def info(self, msg: str, **ctx: Any) -> None:
        self._log.info(self._format(msg, ctx))

    def warning(self, msg: str, **ctx: Any) -> None:
        self._log.warning(self._format(msg, ctx))

    def error(self, msg: str, **ctx: Any) -> None:
        self._log.error(self._format(msg, ctx))

    def exception(self, msg: str, **ctx: Any) -> None:
        self._log.exception(self._format(msg, ctx))


class TimedLogger:
    """Context manager that logs elapsed time on exit."""

    def __init__(self, logger: MeetingLogger, label: str, **ctx: Any) -> None:
        self._logger = logger
        self._label = label
        self._ctx = ctx
        self._start: float = 0.0

    def __enter__(self) -> "TimedLogger":
        self._start = time.monotonic()
        return self

    def __exit__(self, exc_type: Any, *_: Any) -> None:
        elapsed_ms = int((time.monotonic() - self._start) * 1000)
        if exc_type:
            self._logger.error(f"{self._label} failed", elapsed_ms=elapsed_ms, **self._ctx)
        else:
            self._logger.info(f"{self._label} done", elapsed_ms=elapsed_ms, **self._ctx)


def get_logger(name: str) -> MeetingLogger:
    """Return a MeetingLogger for the given sub-namespace."""
    return MeetingLogger(name)
