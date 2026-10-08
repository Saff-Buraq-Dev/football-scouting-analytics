import pytest

from football_platform.board.rules import InvalidBoardInputError, clean_text, normalise_tag


def test_tags_are_case_insensitive_and_single_spaced():
    assert normalise_tag("  Left   Foot ") == "left foot"


@pytest.mark.parametrize("tag", ["", "   ", "x" * 31])
def test_empty_or_long_tags_are_rejected(tag):
    with pytest.raises(InvalidBoardInputError):
        normalise_tag(tag)


def test_optional_text_may_be_empty_but_not_too_long():
    assert clean_text("  ", "Description", 10, required=False) == ""
    with pytest.raises(InvalidBoardInputError):
        clean_text("x" * 11, "Description", 10, required=False)
