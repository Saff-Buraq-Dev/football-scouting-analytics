import pandas as pd
import pytest

from football_platform.analytics.geometry import distance_to_goal, in_penalty_area, is_progressive


def test_distance_to_goal_from_penalty_spot():
    assert distance_to_goal(94.0, 34.0) == pytest.approx(11.0)


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        ((10, 34), (41, 34), True),    # own half -> own half, 31 m gain (>= 30)
        ((10, 34), (39, 34), False),   # own half -> own half, 29 m gain
        ((45, 34), (61, 34), True),    # crossing halfway, 16 m gain (>= 15)
        ((45, 34), (59, 34), False),   # crossing halfway, 14 m gain
        ((60, 34), (71, 34), True),    # opponent half, 11 m gain (>= 10)
        ((60, 34), (69, 34), False),
        # A sideways pass from the touchline to the centre gets 13.3 m closer to goal
        # (38.3 m -> 25 m): progressive in the opponent half, a known property of distance-to-goal rules.
        ((80, 5), (80, 34), True),
    ],
)
def test_progressive_thresholds(start, end, expected):
    assert is_progressive(*start, *end) is expected


def test_progressive_handles_series_and_missing_coordinates():
    s = pd.Series
    result = is_progressive(s([60.0, None]), s([34.0, 34.0]), s([75.0, 90.0]), s([34.0, None]))
    assert result.tolist() == [True, False]


def test_penalty_area_bounds():
    assert in_penalty_area(88.5, 34 + 20.16)
    assert not in_penalty_area(88.4, 34)
    assert not in_penalty_area(100, 34 + 20.2)
