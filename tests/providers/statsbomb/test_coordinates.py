import pytest

from football_platform.canonical.pitch import Point
from football_platform.providers.statsbomb.coordinates import to_canonical_point


@pytest.mark.parametrize(
    ("statsbomb", "expected"),
    [
        ([0, 0], Point(0.0, 68.0)),  # top-left in StatsBomb = top-left in canonical (y flipped)
        ([120, 80], Point(105.0, 0.0)),
        ([60, 40], Point(52.5, 34.0)),  # centre spot
        ([108, 40], Point(94.5, 34.0)),  # penalty spot of the attacked goal
        ([120, 40, 1.2], Point(105.0, 34.0)),  # 3-D shot end location: z ignored here
    ],
)
def test_converts_statsbomb_units_to_metres(statsbomb, expected):
    assert to_canonical_point(statsbomb) == expected


def test_none_location_stays_none():
    assert to_canonical_point(None) is None


def test_marginal_overshoot_is_clamped_to_the_line():
    assert to_canonical_point([120.5, -0.4]) == Point(105.0, 68.0)


def test_location_far_outside_pitch_is_rejected():
    with pytest.raises(ValueError):
        to_canonical_point([130, 40])
