import pandas as pd
import pytest

from football_platform.analytics.shot_zones import ZONE_KEYS, classify, penalty_summary, prepare_shots, zone_summary


@pytest.mark.parametrize(("x", "y", "zone"), [
    (102.0, 34.0, "six_yard"),
    (95.0, 34.0, "box_central"),
    (95.0, 18.0, "box_wide"),       # 16 m from the centre line: inside the box, outside the goal-width corridor
    (84.0, 34.0, "edge"),
    (84.0, 5.0, "outside_wide"),
    (70.0, 34.0, "long_range"),
    (99.5, 34 + 9.16, "six_yard"),  # boundary belongs to the inner zone
])
def test_zone_classification(x, y, zone):
    assert classify(pd.Series([x]), pd.Series([y]))[0] == zone


def shots_frame(rows):
    return pd.DataFrame(rows, columns=["id", "period", "start_x", "start_y", "set_piece", "shot_outcome", "xg"])


def test_summary_conserves_totals_and_excludes_penalties_and_shootouts():
    shots = shots_frame([
        ("a", 1, 102.0, 34.0, None, "goal", 0.6),
        ("b", 1, 95.0, 34.0, None, "saved", 0.2),
        ("c", 2, 70.0, 30.0, None, "off_target", 0.03),
        ("p", 1, 94.0, 34.0, "penalty", "goal", 0.78),
        ("s", 5, 94.0, 34.0, "penalty", "goal", 0.78),
    ])
    summary = zone_summary(prepare_shots(shots)).set_index("zone")
    assert list(summary.index) == ZONE_KEYS
    assert summary["shots"].sum() == 3 and summary["goals"].sum() == 1
    assert summary["npxg"].sum() == pytest.approx(0.83)
    assert summary.loc["six_yard", "share"] == pytest.approx(1 / 3)
    assert pd.isna(summary.loc["edge", "npxg_per_shot"])  # no shots: undefined, not zero
    assert penalty_summary(shots) == {"taken": 1, "scored": 1}
