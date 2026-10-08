import numpy as np
import pandas as pd
import pytest

from football_platform.analytics.zone_maps import ZONES, distribution, progression, receptions, touches, zone_index


@pytest.mark.parametrize(("x", "y", "expected"), [
    (5.0, 34.0, 0 * 5 + 2),     # own goal end, centre
    (100.0, 66.0, 5 * 5 + 4),   # opponent end, LEFT wing (y = 68 is the attacker's left)
    (100.0, 2.0, 5 * 5 + 0),    # opponent end, right wing
    (60.0, 20.0, 3 * 5 + 1),    # right half-space, 4th strip
    (60.0, 13.84, 3 * 5 + 1),   # boundary belongs to the inner channel
])
def test_zone_index_uses_pitch_marking_channels(x, y, expected):
    assert zone_index(pd.Series([x]), pd.Series([y]))[0] == expected


def ev(**kw):
    base = {"period": 1, "type": "pass", "outcome": "success", "set_piece": None,
            "start_x": 40.0, "start_y": 34.0, "end_x": 70.0, "end_y": 34.0}
    return {**base, **kw}


def test_touch_reception_and_progression_selection():
    events = pd.DataFrame([
        ev(),                                                   # touch; progressive (opponent half gain >= 15 m)
        ev(type="carry", outcome="not_applicable", start_x=60.0, end_x=62.0),  # carry: not a touch, not progressive
        ev(type="shot", outcome="fail", start_x=95.0),         # touch
        ev(set_piece="corner", start_x=104.0, end_x=95.0),     # touch, but set piece: no progression
        ev(period=5, type="shot"),                              # shoot-out: excluded
    ])
    assert len(touches(events)) == 3
    assert len(progression(events)) == 1
    received = receptions(pd.DataFrame([ev(), ev(outcome="fail")]))
    assert len(received) == 1 and received.iloc[0]["x"] == 70.0


def test_distribution_counts_every_zone():
    counts = distribution(pd.Series([5.0, 5.0, np.nan]), pd.Series([34.0, 34.0, 10.0]))
    assert len(counts) == ZONES and counts.sum() == 2 and counts[2] == 2
