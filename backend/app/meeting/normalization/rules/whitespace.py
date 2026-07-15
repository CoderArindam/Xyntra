"""Whitespace normalization rule."""
from __future__ import annotations

import re
from typing import Optional

from app.meeting.artifacts.transcript import NormalizedTranscriptSegment
from .base import NormalizationRule

_MULTI_SPACE = re.compile(r"[ \t]+")


class WhitespaceRule(NormalizationRule):
    """Collapse multiple spaces/tabs to a single space and strip edges."""

    @property
    def name(self) -> str:
        return "whitespace"

    def normalize(
        self, segment: NormalizedTranscriptSegment
    ) -> Optional[NormalizedTranscriptSegment]:
        cleaned = _MULTI_SPACE.sub(" ", segment.text).strip()
        if cleaned == segment.text:
            return segment
        return segment.model_copy(
            update={"text": cleaned, "character_count": len(cleaned)}
        )
