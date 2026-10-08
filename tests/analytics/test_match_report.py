import pandas as pd
import pytest

from football_platform.analytics.match_report import (
    elapsed_minutes,
    network_cutoff,
    passing_network,
    period_lengths,
    xg_race,
)

LENGTHS = {1: 47 * 60.0, 2: 48 * 60.0}


def test_elapsed_minutes_do_not_overlap_halves():
    minutes = elapsed_minutes(pd.Series([1, 2]), pd.Series([46 * 60.0, 60.0]), LENGTHS)
    assert minutes.tolist() == pytest.approx([46.0, 48.0])  # 1' of the second half comes after 47' of the first


def test_period_lengths_from_period_end_events():
    events = pd.DataFrame({"type": ["period_end", "period_end", "period_end", "pass"], "period": [1, 1, 2, 2],
                           "time_s": [2820.0, 2821.0, 2880.0, 10.0]})
    assert period_lengths(events) == {1: 2821.0, 2: 2880.0}


def test_xg_race_is_binned_cumulative_and_counts_own_goals_for_the_opponent():
    shots = pd.DataFrame({"team_id": ["h", "a", "h"], "period": [1, 1, 2], "time_s": [120.0, 610.0, 300.0],
                          "xg": [0.3, 0.1, 0.5], "shot_outcome": ["goal", "saved", "saved"]})
    own_goals = pd.DataFrame({"team_id": ["h"], "period": [2], "time_s": [600.0]})  # h player scores for a
    race = xg_race(shots, own_goals, LENGTHS, "h", "a")
    first = race[0]
    assert (first["minute"], first["home_xg"], first["home_goals"]) == (5.0, 0.3, 1)
    assert race[-1]["home_xg"] == pytest.approx(0.8) and race[-1]["away_xg"] == pytest.approx(0.1)
    assert sum(r["away_goals"] for r in race) == 1  # the own goal (minute 57) counts for the away team
    assert race[-1]["minute"] == pytest.approx(95.0)


def team_event(type_, player=None, recipient=None, minute=10.0, period=1, **kw):
    row = {"type": type_, "player_id": player, "pass_recipient_id": recipient, "period": period,
           "time_s": minute * 60, "outcome": "success", "card_type": None,
           "start_x": 30.0, "start_y": 34.0, "end_x": 40.0, "end_y": 30.0}
    row.update(kw)
    return row


def test_network_uses_passes_before_the_first_change_and_hides_rare_links():
    events = pd.DataFrame(
        [team_event("pass", "a", "b") for _ in range(3)]
        + [team_event("pass", "a", "c"), team_event("pass", "b", "a", minute=20)]
        + [team_event("substitution", "c", minute=60)]
        + [team_event("pass", "a", "b", minute=70) for _ in range(5)]  # after the substitution: ignored
    )
    network = passing_network(events, LENGTHS)
    assert (network["cutoff_minute"], network["cutoff_reason"]) == (60.0, "first substitution")
    assert network["completed_passes"] == 5
    assert network["links"] == [{"a": "a", "b": "b", "passes": 4}]  # a<->b both directions; a-c (1) hidden
    node_a = next(n for n in network["nodes"] if n["player_id"] == "a")
    assert node_a["involvement"] == 5  # 4 passes made + 1 received


def test_dismissal_also_ends_the_network():
    events = pd.DataFrame([team_event("card", "a", minute=30, card_type="red")])
    assert network_cutoff(events, LENGTHS).reason == "first dismissal"
