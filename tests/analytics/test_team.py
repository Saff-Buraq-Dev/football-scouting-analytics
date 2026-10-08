import numpy as np
import pandas as pd
import pytest

from football_platform.analytics.team import (
    TEAM_EVENT_COLUMNS,
    expected_points,
    goal_distribution,
    team_match_stats,
    team_season_stats,
)
from tests.analytics.test_player_season import CAPS

MATCHES = pd.DataFrame({
    "id": ["m1"], "season_id": ["s1"], "home_team_id": ["t1"], "away_team_id": ["t2"],
    "home_score": [1], "away_score": [0],
})


def ev(type_, team="t1", **kw):
    row = dict.fromkeys(TEAM_EVENT_COLUMNS)
    row.update(id=f"e{id(kw)}{len(kw)}{type_}{team}{kw.get('start_x')}", match_id="m1", period=1,
               team_id=team, type=type_, outcome="success")
    row.update(kw)
    return row


def xg_frame(pairs):
    return pd.DataFrame([{"event_id": e, "metric_key": "xg", "value": v, "source_provider": "sb",
                          "model_version": "v"} for e, v in pairs],
                        columns=["event_id", "metric_key", "value", "source_provider", "model_version"])


def test_goal_distribution_is_poisson_binomial():
    assert goal_distribution(np.array([0.5, 0.5])) == pytest.approx([0.25, 0.5, 0.25])
    assert goal_distribution(np.array([])) == pytest.approx([1.0])


def test_expected_points_on_hand_computable_cases():
    assert expected_points(np.array([]), np.array([])) == pytest.approx(1.0)  # certain 0-0
    assert expected_points(np.array([1.0]), np.array([])) == pytest.approx(3.0)  # certain 1-0
    # One 0.5 chance each: P(win) = 0.25, P(draw) = 0.5 -> 1.25
    assert expected_points(np.array([0.5]), np.array([0.5])) == pytest.approx(1.25)


def test_total_expected_points_lie_between_two_and_three():
    a, b = np.array([0.3, 0.1, 0.05]), np.array([0.6])
    total = expected_points(a, b) + expected_points(b, a)
    assert 2.0 <= total <= 3.0  # a draw shares 2 points, a win gives 3


def test_ppda_counts_opponent_passes_in_their_60_percent_against_high_defensive_actions():
    events = pd.DataFrame([
        ev("pass", team="t2", start_x=30.0, start_y=34.0, end_x=40.0, end_y=34.0),  # in t2's own 60 %: counts
        ev("pass", team="t2", start_x=50.0, start_y=34.0, end_x=60.0, end_y=34.0),  # counts
        ev("pass", team="t2", start_x=80.0, start_y=34.0, end_x=90.0, end_y=34.0),  # beyond 63 m: not counted
        ev("interception", team="t1", start_x=60.0, start_y=34.0),                  # t1 frame >= 42 m: counts
        ev("interception", team="t1", start_x=20.0, start_y=34.0),                  # deep: not counted
    ], columns=list(TEAM_EVENT_COLUMNS))
    stats = team_match_stats(events, xg_frame([]), MATCHES).set_index("team_id")
    assert stats.loc["t1", "opponent_passes_in_own_60"] == 2
    assert stats.loc["t1", "defensive_actions_high"] == 1
    assert stats.loc["t1", ["points", "goals_for"]].tolist() == [3, 1]


def test_season_ratios_and_shares():
    shot_counter = ev("shot", shot_outcome="goal", possession_origin="counter")
    shot_corner = ev("shot", shot_outcome="saved", possession_origin="corner", start_x=95.0)
    events = pd.DataFrame([shot_counter, shot_corner], columns=list(TEAM_EVENT_COLUMNS))
    team_match = team_match_stats(events, xg_frame([(shot_counter["id"], 0.3), (shot_corner["id"], 0.1)]), MATCHES)
    possession = pd.DataFrame({"match_id": ["m1", "m1"], "team_id": ["t1", "t2"], "possession_pct": [55.0, 45.0]})
    season = team_season_stats(team_match, CAPS, possession).set_index("team_id")
    assert season.loc["t1", "npxg_per_shot_for"] == pytest.approx(0.2)
    assert season.loc["t1", "counter_npxg_share"] == pytest.approx(0.75)
    assert season.loc["t1", "set_piece_npxg_share"] == pytest.approx(0.25)
    assert season.loc["t2", "npxg_against_per_match"] == pytest.approx(0.4)


def test_team_percentiles_are_computed_within_each_league():
    from football_platform.analytics.team import TEAM_METRICS, add_team_percentiles

    rows = []
    for season, values in (("liga", [11.0, 13.0, 15.0]), ("pl", [14.0, 16.0, 18.0])):
        for i, v in enumerate(values):
            rows.append({"team_id": f"{season}{i}", "season_id": season, **{m.key: v for m in TEAM_METRICS}})
    result = add_team_percentiles(pd.DataFrame(rows), ["liga", "pl"]).set_index("team_id")
    # 15.0 is the highest in La Liga but would be below average if the leagues were pooled.
    assert result.loc["liga2", "ppda_pct"] == pytest.approx(100.0)
    assert result.loc["pl0", "ppda_pct"] == pytest.approx(100 / 3)
    assert result.loc["pl0", "league_size"] == 3


def test_defensive_height_and_high_ball_wins():
    events = pd.DataFrame([
        ev("interception", team="t1", start_x=80.0, start_y=34.0),                       # high ball win
        ev("ball_recovery", team="t1", start_x=30.0, start_y=34.0),                      # deep ball win
        ev("duel", team="t1", duel_kind="ground", outcome="fail", start_x=50.0, start_y=34.0),  # action, not a win
    ], columns=list(TEAM_EVENT_COLUMNS))
    team_match = team_match_stats(events, xg_frame([]), MATCHES)
    possession = pd.DataFrame({"match_id": ["m1", "m1"], "team_id": ["t1", "t2"], "possession_pct": [50.0, 50.0]})
    season = team_season_stats(team_match, CAPS, possession).set_index("team_id")
    assert season.loc["t1", "defensive_height_m"] == pytest.approx((80 + 30 + 50) / 3)
    assert season.loc["t1", "high_ball_wins_per_match"] == 1
