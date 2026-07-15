"""Filler word removal rule.

Loads filler dictionaries from JSON config files in
``app/meeting/normalization/config/fillers_<lang>.json``.

Adding a new language requires only dropping a new JSON file — no code changes.

Design decisions:
- Whole-word/phrase boundary matching only (via \\b for Latin, lookahead/lookbehind
  for Unicode scripts that don't have traditional word boundaries).
- Phrases are matched before single words to avoid partial phrase removal.
- Fillers inside meaningful phrases are preserved by the boundary constraint.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.meeting.artifacts.transcript import NormalizedTranscriptSegment
from .base import NormalizationRule

_CONFIG_DIR = Path(__file__).parent.parent / "config"

# Language code normalization: maps detected_language display names to file codes
_LANG_ALIASES: Dict[str, str] = {
    "english": "en",
    "bengali": "bn",
    "hindi": "hi",
    "en": "en",
    "bn": "bn",
    "hi": "hi",
}


@lru_cache(maxsize=16)
def _load_fillers(lang_code: str) -> Tuple[List[str], List[str]]:
    """Load and cache filler words/phrases for a language code."""
    path = _CONFIG_DIR / f"fillers_{lang_code}.json"
    if not path.exists():
        return [], []
    data = json.loads(path.read_text(encoding="utf-8"))
    # Sort phrases longest-first so longer phrases match before sub-phrases
    phrases = sorted(data.get("phrases", []), key=len, reverse=True)
    words = data.get("words", [])
    return phrases, words


def _build_pattern(terms: List[str]) -> Optional[re.Pattern[str]]:
    """Build a Unicode-aware word-boundary pattern for a list of terms."""
    if not terms:
        return None
    escaped = [re.escape(t) for t in terms]
    # Use (?<!\w) / (?!\w) for Unicode boundary — works for Devanagari/Bengali
    joined = "|".join(escaped)
    return re.compile(
        rf"(?<!\w)(?:{joined})(?!\w)",
        re.IGNORECASE | re.UNICODE,
    )


class FillerWordRule(NormalizationRule):
    """Remove language-specific filler words and phrases from segments.

    Filler dictionaries are discovered automatically from
    ``normalization/config/fillers_<lang>.json`` files.
    """

    @property
    def name(self) -> str:
        return "filler_words"

    def normalize(
        self, segment: NormalizedTranscriptSegment
    ) -> Optional[NormalizedTranscriptSegment]:
        lang_key = _LANG_ALIASES.get(segment.language.lower(), segment.language.lower())
        phrases, words = _load_fillers(lang_key)

        if not phrases and not words:
            return segment  # No dictionary for this language — leave untouched

        text = segment.text

        # Remove phrases first (longer terms)
        phrase_pattern = _build_pattern(phrases)
        if phrase_pattern:
            text = phrase_pattern.sub("", text)

        # Remove single filler words
        word_pattern = _build_pattern(words)
        if word_pattern:
            text = word_pattern.sub("", text)

        # Clean up any double spaces left by removal
        text = re.sub(r"[ \t]{2,}", " ", text).strip()

        if text == segment.text:
            return segment

        words_list = text.split()
        return segment.model_copy(
            update={
                "text": text,
                "word_count": len(words_list),
                "character_count": len(text),
            }
        )
