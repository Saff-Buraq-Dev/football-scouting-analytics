import math

import pandas as pd
import pytest

from football_platform.analytics.definitions import RATIO_METRICS
from football_platform.analytics.percentiles import IncompletePopulationError, add_percentiles, percentile_columns

SEASONS = pd.DataFrame({"id": ["s1", "s2"], "coverage_scope": ["complete", "partial"]})


def frame(rows):
    base = {c: 1.0 for c in percentile_columns()}
    base.update({f"{m.key}_reliable": True for m in RATIO_METRICS})
    data = []
    for player, group, value, eligible in rows:
        data.append({**base, "player_id": player, "season_id": "s1", "position_group": group,
                     "eligible": eligible, "np_shots_p90": value})
    return pd.DataFrame(data)


def test_percentiles_are_within_position_group_and_eligible_players():
    df = frame([
        ("a", "striker", 1.0, True), ("b", "striker", 2.0, True), ("c", "striker", 3.0, True),
        ("d", "striker", 9.0, False),  # below minutes threshold: excluded from population
        ("e", "centre_back", 0.5, True),
    ])
    result = add_percentiles(df, SEASONS, ["s1"]).set_index("player_id")
    assert result.loc["c", "np_shots_p90_pct"] == pytest.approx(100.0)
    assert result.loc["a", "np_shots_p90_pct"] == pytest.approx(100 / 3)
    assert result.loc["e", "np_shots_p90_pct"] == pytest.approx(100.0)  # alone in its group
    assert math.isnan(result.loc["d", "np_shots_p90_pct"])
    assert result.loc["a", "population_size"] == 3


def test_ties_share_the_average_rank():
    df = frame([("a", "striker", 1.0, True), ("b", "striker", 1.0, True)])
    result = add_percentiles(df, SEASONS, ["s1"])
    assert result["np_shots_p90_pct"].tolist() == [75.0, 75.0]


def test_partial_coverage_population_is_refused():
    with pytest.raises(IncompletePopulationError):
        add_percentiles(frame([("a", "striker", 1.0, True)]), SEASONS, ["s1", "s2"])


def test_ratio_without_enough_attempts_is_not_ranked():
    df = frame([("a", "striker", 1.0, True), ("b", "striker", 2.0, True)])
    df["pass_completion"] = [0.9, 0.8]
    df["pass_completion_reliable"] = [True, False]
    result = add_percentiles(df, SEASONS, ["s1"]).set_index("player_id")
    assert result.loc["a", "pass_completion_pct"] == 100.0  # alone among reliable players
    assert math.isnan(result.loc["b", "pass_completion_pct"])
