"""Async retry policy with exponential backoff.

Usage:
    result = await with_retry(
        lambda: do_something(),
        max_attempts=3,
        retryable_exceptions=(NetworkError, BrowserLaunchError),
        logger=log,
        session_id=sid,
    )
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, TypeVar

from app.meeting.logger import MeetingLogger

T = TypeVar("T")

_SENTINEL = object()


async def with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 30.0,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    logger: MeetingLogger | None = None,
    **log_ctx: Any,
) -> T:
    """Execute `fn` with exponential backoff on failure.

    Args:
        fn: Zero-argument async callable.
        max_attempts: Total attempts (including the first).
        base_delay: Initial delay before first retry (seconds).
        max_delay: Cap on backoff delay.
        retryable_exceptions: Only retry on these exception types.
        logger: Optional MeetingLogger for structured retry logs.
        **log_ctx: Extra fields forwarded to every log call.

    Returns:
        The return value of `fn` on success.

    Raises:
        The last caught exception if all attempts are exhausted.
    """
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            return await fn()
        except retryable_exceptions as exc:
            last_error = exc
            if attempt == max_attempts:
                break

            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            if logger:
                logger.warning(
                    f"Attempt {attempt}/{max_attempts} failed — retrying in {delay:.1f}s",
                    error=str(exc),
                    **log_ctx,
                )
            await asyncio.sleep(delay)

    raise last_error  # type: ignore[misc]
