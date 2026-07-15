"""Immediate duplicate word removal rule."""
from __future__ import annotations

import re
from typing import Optional

from app.meeting.artifacts.transcript import NormalizedTranscriptSegment
from .base import NormalizationRule

# Matches a word followed immediately by the same word (case-insensitive).
# Handles Unicode words via \w+ — works for Bengali, Hindi, Latin scripts.
_DUP_WORD = re.compile(r"\b(\w+)\s+\1\b", re.IGNORECASE | re.UNICODE)


class DuplicateWordRule(NormalizationRule):
    """Remove immediately consecutive duplicate words.

    Examples:
        "I I think"        → "I think"
        "the the project"  → "the project"

    Only removes *immediate* duplicates.  Semantic deduplication is out of scope.
    Applies repeatedly until no more duplicates remain.
    """

    @property
    def name(self) -> str:
        return "duplicate_words"

    def normalize(
        self, segment: NormalizedTranscriptSegment
    ) -> Optional[NormalizedTranscriptSegment]:
        text = segment.text
        # Apply until stable (handles "a a a" → "a")
        while True:
            new_text = _DUP_WORD.sub(r"\1", text)
            if new_text == text:
                break
            text = new_text

        if text == segment.text:
            return segment

        words = text.split()
        return segment.model_copy(
            update={
                "text": text,
                "word_count": len(words),
                "character_count": len(text),
            }
        )
