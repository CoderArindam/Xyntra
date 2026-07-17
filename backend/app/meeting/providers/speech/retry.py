"""Production-grade async retry engine for speech providers.

Exponential backoff with jitter.  Only retryable failures are retried;
permanent failures propagate immediately.
"""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Optional, Set, Tuple, Type, TypeVar

from app.meeting.exceptions import (
    SpeechProviderAuthError,
    SpeechProviderConfigError,
    SpeechProviderError,
    SpeechProviderRateLimitError,
    SpeechProviderTimeoutError,
    SpeechProviderUnavailableError,
    SpeechProviderValidationError,
)
from app.meeting.logger import get_logger

log = get_logger("speech.retry")

T = TypeVar("T")

# Errors that should never be retried regardless of policy
_PERMANENT_ERROR_TYPES: Tuple[Type[SpeechProviderError], ...] = (
    SpeechProviderAuthError,
    SpeechProviderConfigError,
    SpeechProviderValidationError,
)

# Errors that are always retryable
_RETRYABLE_ERROR_TYPES: Tuple[Type[SpeechProviderError], ...] = (
    SpeechProviderRateLimitError,
    SpeechProviderTimeoutError,
    SpeechProviderUnavailableError,
)


@dataclass
class RetryPolicy:
    max_retries: int = 3
    base_delay: float = 1.0          # seconds
    max_delay: float = 60.0          # seconds
    backoff_factor: float = 2.0
    jitter: bool = True              # adds ±20% random jitter
    retryable_exceptions: Set[Type[Exception]] = field(default_factory=set)

    def delay_for(self, attempt: int) -> float:
        """Compute sleep duration for the given attempt (0-indexed)."""
        raw = min(self.base_delay * (self.backoff_factor ** attempt), self.max_delay)
        if self.jitter:
            raw *= 0.8 + random.random() * 0.4   # ±20%
        return raw


def _is_retryable(exc: Exception) -> bool:
    """Determine if an exception should trigger a retry."""
    if isinstance(exc, _PERMANENT_ERROR_TYPES):
        return False
    if isinstance(exc, _RETRYABLE_ERROR_TYPES):
        return True
    # For generic SpeechProviderError, defer to the .retryable flag
    if isinstance(exc, SpeechProviderError):
        return exc.retryable
    # Non-provider exceptions (network, IO) are retryable
    return True


async def with_retry(
    fn: Callable[[], Awaitable[T]],
    policy: RetryPolicy,
    *,
    context: Optional[str] = None,
) -> Tuple[T, int]:
    """Execute *fn* with retries according to *policy*.

    Returns:
        (result, retry_count) — retry_count is 0 on first-attempt success.

    Raises:
        The last exception if all retries are exhausted.
    """
    label = context or "speech.provider"
    last_exc: Optional[Exception] = None
    retry_count = 0

    for attempt in range(policy.max_retries + 1):
        try:
            result = await fn()
            if attempt > 0:
                log.info(
                    "speech.retry.succeeded",
                    context=label,
                    attempt=attempt,
                    retry_count=retry_count,
                )
            return result, retry_count

        except Exception as exc:
            last_exc = exc

            if not _is_retryable(exc):
                log.error(
                    "speech.retry.permanent_failure",
                    context=label,
                    attempt=attempt,
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
                raise

            if attempt >= policy.max_retries:
                log.error(
                    "speech.retry.exhausted",
                    context=label,
                    max_retries=policy.max_retries,
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
                break

            delay = policy.delay_for(attempt)
            retry_count += 1
            log.warning(
                "speech.retry.retrying",
                context=label,
                attempt=attempt,
                retry_count=retry_count,
                delay_sec=round(delay, 2),
                error_type=type(exc).__name__,
                error=str(exc),
            )
            await asyncio.sleep(delay)

    assert last_exc is not None
    raise last_exc
