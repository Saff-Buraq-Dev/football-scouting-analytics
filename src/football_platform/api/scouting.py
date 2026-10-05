"""Assemble a scouting result (pure logic, no database).

Method: docs/FOOTBALL_ANALYTICS.md, "Phase 7 — Scouting" (filters + Pareto tiers + maximin).
"""

from __future__ import annotations

from typing import Any

from football_platform.analytics.definitions import ALL_METRICS, PositionGroup
from football_platform.analytics.scouting import (
    DEFAULT_NEAR_MISS_POINTS,
    MAX_CRITERIA,
    Candidate,
    Criterion,
    near_misses,
    rank_candidates,
)
from football_platform.analytics.scouting_presets import PRESETS
from football_platform.api.profile import DATA_SOURCE, reliability_band

METRICS = {m.key: m for m in ALL_METRICS}
METHOD = (
    "Candidates meet every criterion (percentile within their position group). Tier 1 = no other candidate "
    "is better on every criterion. Within a tier: highest weakest criterion first, then most minutes. "
    "No weighted score."
)


class InvalidCriteriaError(ValueError):
    pass


def parse_criteria(raw: list[str], position_group: PositionGroup) -> list[Criterion]:
    """'metric:min_percentile' strings -> validated criteria for this position group."""
    if not 1 <= len(raw) <= MAX_CRITERIA:
        raise InvalidCriteriaError(f"Use between 1 and {MAX_CRITERIA} criteria")
    criteria = []
    for item in raw:
        key, _, threshold = item.partition(":")
        if key not in METRICS:
            raise InvalidCriteriaError(f"Unknown metric {key!r}")
        allowed = METRICS[key].position_groups
        if allowed is not None and position_group.value not in allowed:
            raise InvalidCriteriaError(f"{key} is not defined for {position_group.value}")
        try:
            criteria.append(Criterion(key, float(threshold)))
        except ValueError as error:
            raise InvalidCriteriaError(f"Invalid threshold in {item!r}: {error}") from None
    if len({c.metric_key for c in criteria}) != len(criteria):
        raise InvalidCriteriaError("Each metric can be used once")
    return criteria


def _criteria_view(player: dict[str, Any], criteria: list[Criterion]) -> list[dict[str, Any]]:
    view = []
    for c in criteria:
        metric = player["metrics"].get(c.metric_key) or {}
        view.append({
            "key": c.metric_key,
            "percentile": metric.get("percentile"),
            "value": metric.get("value"),
            "reliability_band": reliability_band(metric.get("reliability")),
            "passes": metric.get("percentile") is not None and metric["percentile"] >= c.min_percentile,
        })
    return view


def _player_view(player: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in player.items() if k != "metrics"}


def build_scouting_result(rows: list[dict[str, Any]], criteria: list[Criterion], limit: int,
                          near_miss_points: float = DEFAULT_NEAR_MISS_POINTS) -> dict[str, Any]:
    """rows: one per (player-season, metric) from repository.scouting_population."""
    players: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = f"{row['player_id']}:{row['season_id']}"
        player = players.setdefault(key, {**{k: row[k] for k in (
            "player_id", "season_id", "player_name", "teams", "competition", "season_label",
            "minutes", "team_possession_pct", "primary_role")}, "metrics": {}})
        if row["metric_key"] is not None:
            player["metrics"][row["metric_key"]] = row

    candidates = [
        Candidate(key, float(p["minutes"]), tuple(
            (p["metrics"].get(c.metric_key) or {}).get("percentile") for c in criteria))
        for key, p in players.items()
    ]
    ranked = rank_candidates(candidates, criteria)
    results = [
        {"rank": position, "tier": item.tier, "weakest_percentile": item.weakest_percentile,
         **_player_view(players[item.key]), "criteria": _criteria_view(players[item.key], criteria)}
        for position, item in enumerate(ranked[:limit], start=1)
    ]
    misses = [
        {"gap": gap, "missed": next(cv["key"] for cv in _criteria_view(players[c.key], criteria) if not cv["passes"]),
         **_player_view(players[c.key]), "criteria": _criteria_view(players[c.key], criteria)}
        for c, gap in near_misses(candidates, criteria, near_miss_points)[:limit]
    ]
    return {
        "criteria": [
            {"key": c.metric_key, "label": METRICS[c.metric_key].label, "min_percentile": c.min_percentile,
             "unit": "per_90" if METRICS[c.metric_key].kind.value == "count" else "ratio"}
            for c in criteria
        ],
        "population_size": len(players),
        "shortlisted": len(ranked),
        "tier_1": sum(1 for r in ranked if r.tier == 1),
        "results": results,
        "near_misses": misses,
        "near_miss_points": near_miss_points,
        "method": METHOD,
        "data_source": DATA_SOURCE,
    }


def presets_payload() -> list[dict[str, Any]]:
    return [
        {"key": p.key, "label": p.label, "position_group": p.position_group.value, "intent": p.intent,
         "criteria": [{"key": c.metric_key, "label": METRICS[c.metric_key].label, "min_percentile": c.min_percentile}
                      for c in p.criteria]}
        for p in PRESETS
    ]
