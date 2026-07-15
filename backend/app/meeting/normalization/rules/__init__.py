"""Normalization rules package."""
from .base import NormalizationRule
from .whitespace import WhitespaceRule
from .empty_segment import EmptySegmentRule
from .duplicate_words import DuplicateWordRule
from .repeated_chars import RepeatedCharRule
from .punctuation import PunctuationRule
from .capitalization import CapitalizationRule
from .filler_words import FillerWordRule

__all__ = [
    "NormalizationRule",
    "WhitespaceRule",
    "EmptySegmentRule",
    "DuplicateWordRule",
    "RepeatedCharRule",
    "PunctuationRule",
    "CapitalizationRule",
    "FillerWordRule",
]
