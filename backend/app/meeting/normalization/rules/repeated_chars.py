"""Repeated character cleanup rule — disabled by default.

This rule collapses runs of 3+ identical characters to 2.

IMPORTANT: This rule is intentionally DISABLED by default
(NORMALIZATION_ENABLE_REPEATED_CHARS = False).

Without language-specific dictionaries, collapsing repeated chars is unsafe
across multilingual content:
  - "committee" → "comittee" (wrong)
  - Hindi/Bengali scripts have legitimate character repetition patterns

Enable only when a language-specific correction dictionary is provided.
"""
from __future__ import annotations

import re
from typing import Optional

from app.meeting.artifacts.transcript import NormalizedTranscriptSegment
from .base import NormalizationRule

# Collapse 3+ identical chars to 2: "goooood" → "good" (then 2 may still be wrong)
# We stop at 2 and leave further correction to a future dictionary pass.
_REPEATED_CHARS = re.compile(r"(.)\1{2,}", re.UNICODE)


class RepeatedCharRule(NormalizationRule):
    """Collapse 3+ identical consecutive characters to 2.

    Disabled by default — enable via MEETING_NORMALIZATION_ENABLE_REPEATED_CHARS=true
    only when a language-aware correction dictionary is also in place.
    """

    @property
    def name(self) -> str:
        return "repeated_chars"

    def normalize(
        self, segment: NormalizedTranscriptSegment
    ) -> Optional[NormalizedTranscriptSegment]:
        cleaned = _REPEATED_CHARS.sub(r"\1\1", segment.text)
        if cleaned == segment.text:
            return segment
        return segment.model_copy(
            update={
                "text": cleaned,
                "character_count": len(cleaned),
                "word_count": len(cleaned.split()),
            }
        )
