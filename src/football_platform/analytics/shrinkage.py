"""Regressed (empirical Bayes) per-90 estimates (docs/FOOTBALL_ANALYTICS.md, Phase 4.1 §4).

regressed = w * observed + (1 - w) * group_mean
w         = var_true / (var_true + noise_per_90 / exposure)

The prior (group mean, var_true, noise) is estimated on the eligible players of
the reference population and applied to every player of the group.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from football_platform.analytics.definitions import COUNT_METRICS
from football_platform.analytics.percentiles import check_population

# When the observed spread is no larger than the noise, there is no detectable
# signal: var_true is floored to this fraction of the observed variance (heavy shrinkage).
VAR_TRUE_FLOOR_FRACTION = 0.01


def group_prior(counts: pd.Series, squares: pd.Series, exposure: pd.Series) -> tuple[float, float, float]:
    """(mean rate, var_true, noise per 90) for one metric in one population."""
    rates = counts / exposure
    mean = counts.sum() / exposure.sum()
    noise_per_90 = squares.sum() / exposure.sum()
    var_observed = rates.var(ddof=1)
    var_true = var_observed - (noise_per_90 / exposure).mean()
    return mean, max(var_true, VAR_TRUE_FLOOR_FRACTION * var_observed), noise_per_90


def add_regressed_estimates(
    player_seasons: pd.DataFrame, seasons: pd.DataFrame, population_season_ids: list[str]
) -> pd.DataFrame:
    check_population(seasons, population_season_ids)
    result = player_seasons.copy()
    exposure = result["minutes"] / 90.0
    in_population = result["season_id"].isin(population_season_ids) & result["eligible"]

    for metric in (m for m in COUNT_METRICS if m.regress):
        regressed = pd.Series(np.nan, index=result.index)
        reliability = pd.Series(np.nan, index=result.index)
        available = result[metric.key].notna()
        for group, members in result[available & result["position_group"].notna()].groupby("position_group"):
            population = members[in_population.loc[members.index]]
            if len(population) < 2:
                continue
            mean, var_true, noise = group_prior(
                population[metric.key], population[f"{metric.key}__sq"], exposure.loc[population.index]
            )
            if noise == 0:
                # No event of this kind in the population (e.g. shots by goalkeepers):
                # nothing to regress, the observed value is kept.
                w = pd.Series(1.0, index=members.index)
            else:
                w = var_true / (var_true + noise / exposure.loc[members.index])
            reliability.loc[members.index] = w
            regressed.loc[members.index] = w * members[f"{metric.key}_p90"] + (1 - w) * mean
        result[f"{metric.key}_p90_regressed"] = regressed
        result[f"{metric.key}_reliability"] = reliability
    return result
