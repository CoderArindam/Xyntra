"""Abstract base for all normalization rules."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.meeting.artifacts.transcript import NormalizedTranscriptSegment


class NormalizationRule(ABC):
    """Single-responsibility rule applied to one segment at a time.

    Return the (possibly modified) segment, or ``None`` to remove it
    from the output.  Rules must be stateless and idempotent.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique rule identifier — used as the key in rule_statistics."""

    @abstractmethod
    def normalize(
        self, segment: NormalizedTranscriptSegment
    ) -> Optional[NormalizedTranscriptSegment]:
        """Apply the rule.

        Args:
            segment: Immutable input segment.

        Returns:
            Cleaned segment, or ``None`` to discard it.
        """
