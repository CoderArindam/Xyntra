"""Capitalization normalization rule."""
from __future__ import annotations

import re
from typing import Optional

from app.meeting.artifacts.transcript import NormalizedTranscriptSegment
from .base import NormalizationRule

# Matches standalone "i" (not part of a word) — Latin script only
_STANDALONE_I = re.compile(r"\bi\b")
# Matches start of text or after sentence-ending punctuation
_SENTENCE_START = re.compile(r"((?:^|(?<=[.?!])\s+))([a-z])")


class CapitalizationRule(NormalizationRule):
    """Capitalize sentence starts and standalone 'i'.

    Rules:
      - First character of the segment text → uppercase.
      - First character after '. ', '? ', '! ' → uppercase.
      - Standalone 'i' → 'I' (Latin script only).

    No grammar correction is attempted.
    """

    @property
    def name(self) -> str:
        return "capitalization"

    def normalize(
        self, segment: NormalizedTranscriptSegment
    ) -> Optional[NormalizedTranscriptSegment]:
        text = segment.text
        if not text:
            return segment

        # Capitalize sentence starts
        text = _SENTENCE_START.sub(lambda m: m.group(1) + m.group(2).upper(), text)

        # Capitalize segment-initial character if lowercase
        if text and text[0].islower():
            text = text[0].upper() + text[1:]

        # Standalone 'i' → 'I'
        text = _STANDALONE_I.sub("I", text)

        if text == segment.text:
            return segment
        return segment.model_copy(update={"text": text})
