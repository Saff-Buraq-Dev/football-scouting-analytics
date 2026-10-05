import math
from dataclasses import replace

import pandas as pd
import pytest

from football_platform.analytics.player_match import player_match_stats
from football_platform.analytics.player_season import player_season_stats
from football_platform.analytics.possession import team_match_possession
from football_platform.canonical.capabilities import PositionGranularity, ProviderCapabilities, TimePrecision
from tests.analytics.builders import ev, events, matches, metrics
from tests.analytics.builders import spells as spell_frame

CAPS = ProviderCapabilities(
    provider="statsbomb_open", source_coordinate_system="x", has_event_end_locations=True,
    has_provider_xg=True, has_pressure_events=True, has_carries=True, has_ball_receipts=True,
    has_freeze_frames=False, has_possession_ids=True, has_player_birth_date=False,
    has_position_spells=True, position_granularity=PositionGranularity.SLOT,
    minutes_precision=TimePrecision.SECOND,
)
MATCHES = matches()


def appearances(rows):
    return pd.DataFrame(rows, columns=["match_id", "team_id", "player_id", "is_starter", "minutes_played"])


def spells(rows):
    return pd.DataFrame(rows, columns=["match_id", "player_id", "role", "start_s", "end_s"])


def season(evs, apps, sp, xg=(), caps=CAPS, min_minutes=900):
    pm = player_match_stats(events(*evs), metrics(*xg), spell_frame(), MATCHES)
    possession = team_match_possession(events(*evs))
    return player_season_stats(
        pm, appearances(apps), spells(sp), MATCHES, caps, possession, min_minutes
    ).set_index("player_id")


def test_per90_and_aggregation_across_matches_and_clubs():
    shot1, shot2 = ev("shot", match="m1", team="t1", shot_outcome="goal"), ev("shot", match="m2", team="t2", shot_outcome="saved")
    apps = [("m1", "t1", "p1", True, 90.0), ("m2", "t2", "p1", False, 45.0)]
    sp = [("m1", "p1", "CF", 0, 5400), ("m2", "p1", "CF", 0, 2700)]
    row = season([shot1, shot2], apps, sp, xg=[(shot1["id"], 0.5), (shot2["id"], 0.1)]).loc["p1"]
    assert (row.minutes, row.appearances, row.starts) == (135.0, 2, 1)
    assert row.team_ids == ("t1", "t2")
    assert row.np_shots_p90 == pytest.approx(2 / 135 * 90)
    assert row.npxg_per_shot == pytest.approx(0.3)
    assert not row.eligible


def test_player_without_events_gets_zero_counts_not_missing():
    row = season([], [("m1", "t1", "p1", True, 95.0)], [("m1", "p1", "CB", 0, 5700)]).loc["p1"]
    assert row.np_shots == 0 and row.np_shots_p90 == 0
    assert math.isnan(row.pass_completion)  # no attempts: ratio undefined, not 0


def test_unused_substitute_is_not_a_player_season():
    result = season([], [("m1", "t1", "p1", False, 0.0)], [])
    assert "p1" not in result.index


def test_primary_role_is_the_role_with_most_minutes():
    sp = [("m1", "p1", "W", 0, 1000), ("m1", "p1", "CF", 1000, 5400)]
    row = season([], [("m1", "t1", "p1", True, 90.0)], sp).loc["p1"]
    assert (row.primary_role, row.position_group) == ("CF", "striker")
    assert row.primary_role_share == pytest.approx(4400 / 5400)


def test_capability_gating_gives_nan_not_zero():
    no_xg = replace(CAPS, has_provider_xg=False, has_pressure_events=False)
    press = ev("pressure")
    row = season([press], [("m1", "t1", "p1", True, 90.0)], [("m1", "p1", "CM", 0, 5400)], caps=no_xg).loc["p1"]
    assert math.isnan(row.npxg) and math.isnan(row.xa_p90) and math.isnan(row.pressures_p90)
    assert row.tackles_p90 == 0  # an available metric stays a real zero


def test_eligibility_threshold():
    apps = [("m1", "t1", "p1", True, 950.0)]
    assert season([], apps, [("m1", "p1", "CB", 0, 100)]).loc["p1", "eligible"]


def test_ratio_reliability_flags_and_goalkeeper_metrics_only_for_goalkeepers():
    passes = [ev("pass", match="m1", player="p1", outcome="success")] * 5
    apps = [("m1", "t1", "p1", True, 90.0), ("m1", "t1", "k1", True, 90.0)]
    sp = [("m1", "p1", "CM", 0, 5400), ("m1", "k1", "GK", 0, 5400)]
    result = season(passes, apps, sp)
    cm, gk = result.loc["p1"], result.loc["k1"]
    assert cm.pass_completion == 1.0 and not cm.pass_completion_reliable  # 5 < 100 attempts
    assert math.isnan(cm.gk_np_save_pct) and math.isnan(cm.gk_claims_p90)
    assert gk.gk_claims_p90 == 0


def test_team_possession_context_is_weighted_by_the_players_minutes():
    # m1: t1 has 3 of 4 passes (75 %); m2: t1 has 1 of 4 (25 %). p1 plays 90 then 30 minutes.
    rows = [ev("pass", match="m1", team="t1", player="x")] * 3 + [ev("pass", match="m1", team="t2", player="y")]
    rows += [ev("pass", match="m2", team="t1", player="x")] + [ev("pass", match="m2", team="t2", player="y")] * 3
    apps = [("m1", "t1", "p1", True, 90.0), ("m2", "t1", "p1", False, 30.0)]
    sp = [("m1", "p1", "CB", 0, 5400), ("m2", "p1", "CB", 0, 1800)]
    row = season(rows, apps, sp).loc["p1"]
    assert row.team_possession_pct == pytest.approx((75 * 90 + 25 * 30) / 120)
