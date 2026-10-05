import pandas as pd
import pytest

from football_platform.analytics.player_match import MixedProviderMetricError, player_match_stats
from tests.analytics.builders import ev, events, matches, metrics, spells


def stats_for(*rows, xg=(), spell_rows=()):
    result = player_match_stats(events(*rows), metrics(*xg), spells(*spell_rows), matches())
    return result.set_index("player_id")


def test_penalties_are_excluded_from_npxg_and_np_goals():
    shot = ev("shot", shot_outcome="goal", start_x=95, start_y=34)
    pen = ev("shot", shot_outcome="goal", set_piece="penalty", start_x=94, start_y=34)
    row = stats_for(shot, pen, xg=[(shot["id"], 0.4), (pen["id"], 0.78)]).loc["p1"]
    assert (row.np_shots, row.np_goals, row.penalty_goals) == (1, 1, 1)
    assert row.npxg == pytest.approx(0.4)


def test_shootout_is_ignored():
    shootout = ev("shot", shot_outcome="goal", set_piece="penalty", period=5)
    assert stats_for(shootout).empty


def test_xa_is_the_xg_of_the_assisted_shot_credited_to_the_passer():
    shot = ev("shot", player="striker", shot_outcome="saved")
    key_pass = ev("pass", player="creator", pass_is_shot_assist=True, pass_assisted_shot_event_id=shot["id"])
    result = stats_for(shot, key_pass, xg=[(shot["id"], 0.25)])
    assert result.loc["creator", "xa"] == pytest.approx(0.25)
    assert result.loc["creator", "key_passes"] == 1
    assert result.loc["creator", "assists"] == 0
    assert result.loc["striker", "xa"] == 0


def test_pass_attempts_exclude_injury_clearances():
    rows = [
        ev("pass", outcome="success"),
        ev("pass", outcome="fail"),
        ev("pass", outcome="not_applicable"),
        ev("pass", outcome="unknown"),
    ]
    row = stats_for(*rows).loc["p1"]
    assert (row.passes_attempted, row.passes_completed) == (2, 1)


def test_progressive_passes_must_be_completed_open_play():
    forward = dict(start_x=60, start_y=34, end_x=80, end_y=34)
    rows = [
        ev("pass", **forward),
        ev("pass", outcome="fail", **forward),
        ev("pass", set_piece="free_kick", **forward),
    ]
    assert stats_for(*rows).loc["p1", "progressive_passes"] == 1


def test_box_entries_do_not_count_passes_inside_the_box():
    rows = [
        ev("pass", start_x=80, start_y=34, end_x=95, end_y=34),  # into the box
        ev("pass", start_x=92, start_y=30, end_x=95, end_y=34),  # within the box
    ]
    assert stats_for(*rows).loc["p1", "passes_into_box"] == 1


def test_aerials_combine_won_flags_and_lost_duels():
    rows = [
        ev("clearance", aerial_won=True),
        ev("pass", aerial_won=True),
        ev("duel", duel_kind="aerial", outcome="fail"),
        ev("duel", duel_kind="ground", outcome="success"),
    ]
    row = stats_for(*rows).loc["p1"]
    assert (row.aerials_won, row.aerials_lost, row.aerials_total) == (2, 1, 3)
    assert (row.tackles, row.tackles_won) == (1, 1)


def test_mixing_xg_providers_is_refused():
    a, b = ev("shot", shot_outcome="saved"), ev("shot", shot_outcome="saved")
    mixed = pd.concat(
        [metrics((a["id"], 0.1)), metrics((b["id"], 0.2), provider="opta", version="opta_xg")], ignore_index=True
    )
    with pytest.raises(MixedProviderMetricError):
        player_match_stats(events(a, b), mixed, spells(), matches())
