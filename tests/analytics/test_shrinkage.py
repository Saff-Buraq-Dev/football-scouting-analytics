import numpy as np
import pandas as pd
import pytest

from football_platform.analytics.shrinkage import add_regressed_estimates, group_prior

SEASONS = pd.DataFrame({"id": ["s1"], "coverage_scope": ["complete"]})


def test_group_prior_separates_signal_from_poisson_noise():
    # Rates 0.2 and 0.6 per 90 over 30 x 90 minutes each.
    counts = pd.Series([6.0, 18.0])
    exposure = pd.Series([30.0, 30.0])
    mean, var_true, noise = group_prior(counts, counts, exposure)
    assert mean == pytest.approx(0.4)
    assert noise == pytest.approx(0.4)  # event counts: squared contributions = counts
    assert var_true == pytest.approx(0.08 - 0.4 / 30)


def frame(rows):
    """rows: (player, minutes, count, eligible) for one metric (np_goals) in one group."""
    data = []
    for player, minutes, count, eligible in rows:
        data.append({"player_id": player, "season_id": "s1", "position_group": "striker", "eligible": eligible,
                     "minutes": minutes, "np_goals": count, "np_goals__sq": count,
                     "np_goals_p90": count / minutes * 90})
    df = pd.DataFrame(data)
    for key in ("np_shots", "npxg", "assists", "key_passes", "xa", "progressive_passes", "progressive_carries",
                "passes_into_final_third", "passes_into_box", "tackles", "interceptions",
                "ball_recoveries", "pressures", "aerials_won", "gk_claims", "gk_sweeper_actions"):
        df[key] = np.nan
    return df


def test_low_minute_players_are_pulled_more_towards_the_group_mean():
    rows = [(f"p{i}", 2700, c, True) for i, c in enumerate([5, 10, 15, 20, 25])]
    rows += [("short", 450, 5, False), ("long", 2700, 25, True)]
    result = add_regressed_estimates(frame(rows), SEASONS, ["s1"]).set_index("player_id")
    short, long = result.loc["short"], result.loc["long"]
    assert short["np_goals_reliability"] < long["np_goals_reliability"]
    # 'short' has a high observed rate (1.0 per 90) on 450 minutes: strongly regressed.
    assert short["np_goals_p90_regressed"] < short["np_goals_p90"]
    assert abs(short["np_goals_p90_regressed"] - short["np_goals_p90"]) > abs(
        long["np_goals_p90_regressed"] - long["np_goals_p90"]
    )


def test_unavailable_metric_gets_no_regressed_estimate():
    rows = [(f"p{i}", 2700, c, True) for i, c in enumerate([5, 10, 15])]
    result = add_regressed_estimates(frame(rows), SEASONS, ["s1"])
    assert result["npxg_p90_regressed"].isna().all()


def test_metric_without_any_event_in_the_group_keeps_the_observed_value():
    rows = [(f"p{i}", 2700, 0, True) for i in range(3)] + [("short", 300, 0, False)]
    result = add_regressed_estimates(frame(rows), SEASONS, ["s1"])
    assert (result["np_goals_p90_regressed"] == 0).all()
    assert (result["np_goals_reliability"] == 1).all()


def test_posterior_sd_shrinks_with_more_minutes_and_matches_the_formula():
    rows = [(f"p{i}", 2700, c, True) for i, c in enumerate([5, 10, 15, 20, 25])]
    rows += [("short", 450, 5, False)]
    result = add_regressed_estimates(frame(rows), SEASONS, ["s1"]).set_index("player_id")
    assert result.loc["short", "np_goals_p90_regressed_sd"] > result.loc["p0", "np_goals_p90_regressed_sd"]
    # sd = sqrt(w * noise / exposure); noise = pooled per-90 rate of squared contributions.
    pool = result.loc[[f"p{i}" for i in range(5)]]
    noise = pool["np_goals__sq"].sum() / (pool["minutes"].sum() / 90)
    w = result.loc["short", "np_goals_reliability"]
    assert result.loc["short", "np_goals_p90_regressed_sd"] == pytest.approx(np.sqrt(w * noise / 5))
