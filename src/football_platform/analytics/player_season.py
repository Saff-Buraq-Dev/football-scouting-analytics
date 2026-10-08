"""Player x competition-season statistics: totals, per 90, ratios, primary position.

Definitions: docs/FOOTBALL_ANALYTICS.md, "Phase 4 — Player season metrics".
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from football_platform.analytics.definitions import (
    COUNT_METRICS,
    DEFAULT_MIN_MINUTES,
    MetricKind,
    MetricSpec,
    POSITION_GROUP_BY_ROLE,
    RATIO_METRICS,
)
from football_platform.canonical.capabilities import ProviderCapabilities
from football_platform.canonical.enums import PositionRole

SEASON_KEYS = ["player_id", "season_id"]
# Deterministic tie-break when two roles have exactly the same minutes.
ROLE_ORDER = {role.value: i for i, role in enumerate(PositionRole)}


def _metric_columns(metric: MetricSpec) -> list[str]:
    return [metric.key, f"{metric.key}_p90"] if metric.kind is MetricKind.COUNT else [metric.key]


def primary_roles(position_spells: pd.DataFrame, matches: pd.DataFrame) -> pd.DataFrame:
    """Role with the most minutes per player-season (and its share of the player's minutes)."""
    spells = position_spells.merge(matches[["id", "season_id"]], left_on="match_id", right_on="id")
    spells = spells.assign(seconds=spells["end_s"] - spells["start_s"])
    by_role = spells.groupby(SEASON_KEYS + ["role"], as_index=False)["seconds"].sum()
    by_role["order"] = by_role["role"].map(ROLE_ORDER)
    by_role = by_role.sort_values(SEASON_KEYS + ["seconds", "order"], ascending=[True, True, False, True])
    totals = by_role.groupby(SEASON_KEYS)["seconds"].transform("sum")
    by_role["primary_role_share"] = by_role["seconds"] / totals
    primary = by_role.drop_duplicates(SEASON_KEYS, keep="first")
    primary = primary.rename(columns={"role": "primary_role"})
    primary["position_group"] = primary["primary_role"].map(
        {role.value: group.value for role, group in POSITION_GROUP_BY_ROLE.items()}
    )
    return primary[SEASON_KEYS + ["primary_role", "primary_role_share", "position_group"]]


def player_season_stats(
    player_match: pd.DataFrame,
    appearances: pd.DataFrame,
    position_spells: pd.DataFrame,
    matches: pd.DataFrame,
    capabilities: ProviderCapabilities,
    team_possession: pd.DataFrame,
    min_minutes: float = DEFAULT_MIN_MINUTES,
) -> pd.DataFrame:
    """One row per player-season with totals, per-90 values, ratios and eligibility.

    `team_possession` (match_id, team_id, possession_pct) gives the context column
    `team_possession_pct`: the possession of the player's team, weighted by his
    minutes in each match (decision D017: context, not adjustment).
    """
    season_of = matches[["id", "season_id"]].rename(columns={"id": "match_id"})
    apps = appearances.merge(season_of, on="match_id")
    playing = apps.groupby(SEASON_KEYS).agg(
        minutes=("minutes_played", "sum"),
        appearances=("minutes_played", lambda m: int((m > 0).sum())),
        starts=("is_starter", "sum"),
        team_ids=("team_id", lambda t: tuple(sorted(set(t)))),
    ).reset_index()
    playing = playing[playing["minutes"] > 0]
    weighted = apps.merge(team_possession, on=["match_id", "team_id"], how="left")
    weighted = weighted[weighted["minutes_played"] > 0].assign(
        poss_minutes=lambda d: d["possession_pct"] * d["minutes_played"]
    )
    context = weighted.groupby(SEASON_KEYS)[["poss_minutes", "minutes_played"]].sum()
    playing = playing.merge(
        (context["poss_minutes"] / context["minutes_played"]).rename("team_possession_pct").reset_index(),
        on=SEASON_KEYS,
        how="left",
    )

    count_keys = [m.key for m in COUNT_METRICS]
    count_keys += [f"{k}__sq" for k in count_keys] + ["aerials_total"]
    totals = (
        player_match.merge(season_of, on="match_id")
        .groupby(SEASON_KEYS)[count_keys].sum(min_count=1)  # all-NaN (unavailable) stays NaN
        .reset_index()
    )
    stats = playing.merge(totals, on=SEASON_KEYS, how="left")
    # Played but no relevant events -> 0; metrics declared unavailable (e.g. no xT model) stay NaN.
    unavailable = player_match.attrs.get("unavailable_metrics", frozenset())
    available = [k for k in count_keys if k.removesuffix("__sq") not in unavailable]
    stats[available] = stats[available].fillna(0)
    stats = stats.merge(primary_roles(position_spells, matches), on=SEASON_KEYS, how="left")

    derived: dict[str, pd.Series] = {}
    for metric in COUNT_METRICS:
        derived[f"{metric.key}_p90"] = stats[metric.key] / stats["minutes"] * 90
    for metric in RATIO_METRICS:
        derived[metric.key] = stats[metric.numerator] / stats[metric.denominator].replace(0, np.nan)
        # Ranked only with enough attempts (Phase 4.1 §1); the value stays visible.
        derived[f"{metric.key}_reliable"] = stats[metric.denominator] >= metric.min_denominator
    stats = pd.concat([stats, pd.DataFrame(derived)], axis=1)

    # Position-specific metrics (e.g. goalkeeping) are undefined for other groups.
    for metric in COUNT_METRICS + RATIO_METRICS:
        if metric.position_groups is not None:
            outside = ~stats["position_group"].isin(metric.position_groups)
            stats.loc[outside, _metric_columns(metric)] = np.nan

    # Capability gating: unavailable is NaN, never zero (docs/ARCHITECTURE.md §3).
    for metric in COUNT_METRICS + RATIO_METRICS:
        if metric.capability and not getattr(capabilities, metric.capability):
            stats[_metric_columns(metric)] = np.nan

    stats["eligible"] = stats["minutes"] >= min_minutes
    stats["min_minutes"] = min_minutes
    stats["source_provider"] = capabilities.provider
    return stats
