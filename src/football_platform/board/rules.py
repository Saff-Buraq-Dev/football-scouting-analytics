"""Input rules for board data. The database enforces the same limits (migration 0009)."""

from __future__ import annotations

import re

MAX_SHORTLIST_NAME = 80
MAX_DESCRIPTION = 500
MAX_TAG = 30
MAX_NOTE = 5000


class InvalidBoardInputError(ValueError):
    pass


def clean_text(value: str, field: str, max_length: int, required: bool = True) -> str:
    text = value.strip()
    if required and not text:
        raise InvalidBoardInputError(f"{field} is required")
    if len(text) > max_length:
        raise InvalidBoardInputError(f"{field} is longer than {max_length} characters")
    return text


def normalise_tag(tag: str) -> str:
    """Tags are case-insensitive and single-spaced: "  Left  Foot " and "left foot" are the same tag."""
    return clean_text(re.sub(r"\s+", " ", tag).lower(), "Tag", MAX_TAG)
