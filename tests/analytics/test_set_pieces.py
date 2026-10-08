import pandas as pd
import pytest

from football_platform.analytics.set_pieces import corner_outcomes, corner_summary, delivery_zone


@pytest.mark.parametrize(("start_y", "end_x", "end_y", "zone"), [
    (68.0, 102.0, 40.0, "six_yard_near"),   # taker on the left, ball to the near post
    (68.0, 102.0, 28.0, "six_yard_far"),
    (0.0, 102.0, 28.0, "six_yard_near"),    # taker on the right: mirrored, y = 28 is now the near post
    (68.0, 94.0, 34.0, "penalty_spot"),
    (68.0, 95.0, 50.0, "box_near_side"),
    (68.0, 95.0, 18.0, "box_far_side"),
    (68.0, 100.0, 66.0, "short"),           # beyond the box line
    (68.0, 80.0, 34.0, "short"),            # edge of the box
])
def test_delivery_zones_are_relative_to_the_taker(start_y, end_x, end_y, zone):
    assert delivery_zone(pd.Series([start_y]), pd.Series([end_x]), pd.Series([end_y]))[0] == zone


def ev(id_, type_, minute, possession="7", set_piece=None, shot_outcome=None, team="t1", **kw):
    row = {"id": id_, "match_id": "m", "team_id": team, "period": 1, "time_s": minute * 60.0, "type": type_,
           "set_piece": set_piece, "start_y": 68.0, "end_x": 102.0, "end_y": 40.0,
           "shot_outcome": shot_outcome, "possession_id": possession}
    row.update(kw)
    return row


def test_corner_outcome_counts_shots_of_the_same_possession_after_the_corner():
    events = pd.DataFrame([
        ev("c1", "pass", 10, set_piece="corner"),
        ev("s1", "shot", 10.1, shot_outcome="saved"),
        ev("s2", "shot", 10.3, shot_outcome="goal"),
        ev("s3", "shot", 30, possession="9", shot_outcome="goal"),     # another possession
        ev("c2", "pass", 50, possession="12", set_piece="corner", end_x=90.0, end_y=60.0),
    ])
    out = corner_outcomes(events, pd.Series({"s1": 0.1, "s2": 0.3, "s3": 0.5})).set_index("id")
    assert out.loc["c1", ["shots", "goals"]].tolist() == [2, 1]
    assert out.loc["c1", "xg"] == pytest.approx(0.4)
    assert out.loc["c2", "shots"] == 0
    summary = corner_summary(out.reset_index(), matches=2)
    assert (summary["corners"], summary["per_match"], summary["goals"]) == (2, 1.0, 1)
    assert summary["shot_rate"] == 0.5


def test_outcomes_unavailable_without_possession_ids():
    events = pd.DataFrame([ev("c1", "pass", 10, possession=None, set_piece="corner")])
    summary = corner_summary(corner_outcomes(events, pd.Series(dtype=float)), matches=1)
    assert summary["corners"] == 1 and summary["xg_per_corner"] is None
