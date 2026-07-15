"""Empty segment removal rule."""
from __future__ import annotations

from typing import Optional

from app.meeting.artifacts.transcript import NormalizedTranscriptSegment
from .base import NormalizationRule


class EmptySegmentRule(NormalizationRule):
    """Remove segments whose text is empty, whitespace-only, or None."""

    @property
    def name(self) -> str:
        return "empty_segment"

    def normalize(
        self, segment: NormalizedTranscriptSegment
    ) -> Optional[NormalizedTranscriptSegment]:
        if not segment.text or not segment.text.strip():
            return None
        return segment
