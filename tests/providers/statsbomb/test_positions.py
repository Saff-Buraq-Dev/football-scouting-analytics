import pytest

from football_platform.canonical.enums import PositionLine, PositionRole, Side
from football_platform.providers.statsbomb.positions import POSITION_MAP, to_canonical_position

# The 25 positions of the StatsBomb specification.
STATSBOMB_POSITIONS = [
    "Goalkeeper", "Right Back", "Right Center Back", "Center Back", "Left Center Back",
    "Left Back", "Right Wing Back", "Left Wing Back", "Right Defensive Midfield",
    "Center Defensive Midfield", "Left Defensive Midfield", "Right Midfield",
    "Right Center Midfield", "Center Midfield", "Left Center Midfield", "Left Midfield",
    "Right Wing", "Right Attacking Midfield", "Center Attacking Midfield",
    "Left Attacking Midfield", "Left Wing", "Right Center Forward", "Center Forward",
    "Left Center Forward", "Secondary Striker",
]


def test_every_statsbomb_position_is_mapped():
    assert set(STATSBOMB_POSITIONS) == set(POSITION_MAP)


def test_wide_midfielder_is_distinguished_from_central_midfielder():
    assert to_canonical_position("Right Midfield").role is PositionRole.WM
    assert to_canonical_position("Right Center Midfield").role is PositionRole.CM


def test_left_center_back():
    position = to_canonical_position("Left Center Back")
    assert (position.line, position.role, position.side) == (PositionLine.DEF, PositionRole.CB, Side.LEFT)


def test_unknown_position_fails_loudly():
    with pytest.raises(ValueError):
        to_canonical_position("Sweeper")
