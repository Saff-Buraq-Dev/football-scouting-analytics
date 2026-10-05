"""Percentile ranks within a documented reference population.

Population = eligible players (minutes threshold) of complete-coverage seasons
(decision D010), in the same position group, across the given seasons.
Percentile = average rank / population size x 100 (ties share their average rank).
"""

from __future__ import annotations

import pandas as pd

from football_platform.analytics.definitions import ALL_METRICS, MetricKind
from football_platform.canonical.enums import CoverageScope


class IncompletePopulationError(ValueError):
    pass


def percentile_columns() -> list[str]:
    """Values that get a percentile: per-90 for counts, raw for ratios."""
    return [f"{m.key}_p90" if m.kind is MetricKind.COUNT else m.key for m in ALL_METRICS]


def check_population(seasons: pd.DataFrame, population_season_ids: list[str]) -> None:
    coverage = seasons.set_index("id")["coverage_scope"]
    incomplete = [s for s in population_season_ids if coverage.get(s) != CoverageScope.COMPLETE.value]
    if incomplete:
        raise IncompletePopulationError(f"Seasons without complete coverage: {incomplete}")


def add_percentiles(
    player_seasons: pd.DataFrame, seasons: pd.DataFrame, population_season_ids: list[str]
) -> pd.DataFrame:
    """Add `<column>_pct` columns plus population metadata.

    `seasons` must contain id and coverage_scope. Requesting a population that
    includes a season without complete coverage raises: percentiles on partial
    seasons are biased (docs/FOOTBALL_ANALYTICS.md, "Data coverage").
    """
    check_population(seasons, population_season_ids)
    result = player_seasons.copy()
    in_population = (
        result["season_id"].isin(population_season_ids)
        & result["eligible"]
        & result["position_group"].notna()
    )
    population = result[in_population]
    for metric in ALL_METRICS:
        column = f"{metric.key}_p90" if metric.kind is MetricKind.COUNT else metric.key
        values = population[column]
        if metric.kind is MetricKind.RATIO:
            # Too few attempts: not ranked, and not part of the population (Phase 4.1 §1).
            values = values.where(population[f"{metric.key}_reliable"])
        result[f"{column}_pct"] = values.groupby(population["position_group"]).rank(method="average", pct=True) * 100
    result["population_size"] = population.groupby("position_group")["player_id"].transform("size")
    result["population_seasons"] = ",".join(sorted(population_season_ids))
    return result
