"""Punctuation normalization rule."""
from __future__ import annotations

import re
from typing import Optional

from app.meeting.artifacts.transcript import NormalizedTranscriptSegment
from .base import NormalizationRule

# Multiple commas → single comma
_MULTI_COMMA = re.compile(r",{2,}")
# Multiple periods → single period
_MULTI_PERIOD = re.compile(r"\.{2,}")
# Multiple question marks → single
_MULTI_QUESTION = re.compile(r"\?{2,}")
# Multiple exclamation marks → single
_MULTI_EXCLAIM = re.compile(r"!{2,}")
# Missing space after sentence-ending punctuation (before uppercase or digit)
_MISSING_SPACE = re.compile(r"([.?!,;:])([^\s])")


class PunctuationRule(NormalizationRule):
    """Normalize broken or redundant punctuation patterns.

    Handles:
      - Double/multiple commas:       "hello,,"  → "hello,"
      - Multiple periods:             "okay...."  → "okay."
      - Multiple ?/!:                 "really???" → "really?"
      - Missing space after punct:    "Hello,world" → "Hello, world"
    """

    @property
    def name(self) -> str:
        return "punctuation"

    def normalize(
        self, segment: NormalizedTranscriptSegment
    ) -> Optional[NormalizedTranscriptSegment]:
        text = segment.text
        text = _MULTI_COMMA.sub(",", text)
        text = _MULTI_PERIOD.sub(".", text)
        text = _MULTI_QUESTION.sub("?", text)
        text = _MULTI_EXCLAIM.sub("!", text)
        text = _MISSING_SPACE.sub(r"\1 \2", text)

        if text == segment.text:
            return segment
        return segment.model_copy(
            update={
                "text": text,
                "character_count": len(text),
                "word_count": len(text.split()),
            }
        )
