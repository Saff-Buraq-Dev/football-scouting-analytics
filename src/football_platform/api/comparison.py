"""Assemble a 2-4 player comparison (pure logic, no database).

Rules: docs/FOOTBALL_ANALYTICS.md, "Phase 6 — Player comparison".
"""

from __future__ import annotations

from typing import Any

from football_platform.analytics.comparison import DifferenceVerdict, Estimate, difference_verdict, leader_verdict
from football_platform.analytics.definitions import PositionGroup
from football_platform.analytics.profile_templates import POSSESSION_SENSITIVE, TEMPLATES, THEME_LABELS, Theme
from football_platform.api.profile import DATA_SOURCE, METRICS, metric_view

MIN_PLAYERS = 2
MAX_PLAYERS = 4


def comparison_metrics(groups: list[str | None]) -> list[tuple[Theme, list[str]]]:
    """Union of the players' templates: first player's group first, theme order preserved."""
    ordered_groups = list(dict.fromkeys(g for g in groups if g))
    themes: dict[Theme, list[str]] = {}
    for group in ordered_groups:
        for theme, keys in TEMPLATES[PositionGroup(group)].items():
            bucket = themes.setdefault(theme, [])
            bucket.extend(k for k in keys if k not in bucket)
    return list(themes.items())


def _estimate(metric: dict[str, Any] | None) -> Estimate:
    metric = metric or {}
    return Estimate(metric.get("regressed"), metric.get("regressed_sd"))


def build_comparison(player_seasons: list[dict[str, Any]], metrics: list[dict[str, dict[str, Any]]]) -> dict[str, Any]:
    """player_seasons[i] and metrics[i] describe the same player-season (see api.profile)."""
    if not MIN_PLAYERS <= len(player_seasons) <= MAX_PLAYERS:
        raise ValueError(f"Compare between {MIN_PLAYERS} and {MAX_PLAYERS} player-seasons")

    groups = [ps.get("position_group") for ps in player_seasons]
    same_group = len(set(groups)) == 1
    warnings = []
    if not same_group:
        warnings.append("mixed_position_groups")
    if any(not ps["eligible"] for ps in player_seasons):
        warnings.append("some_players_not_ranked")
    if len({ps["competition"] for ps in player_seasons}) > 1:
        warnings.append("different_competitions")

    themes = []
    for theme, keys in comparison_metrics(groups):
        rows = []
        for key in keys:
            # A metric outside a player's group (e.g. save % for an outfielder) is undefined for him.
            values = [
                {**metric_view(key, m.get(key), bool(ps["eligible"])), "regressed_sd": (m.get(key) or {}).get("regressed_sd")}
                for ps, m in zip(player_seasons, metrics)
            ]
            estimates = [_estimate(m.get(key)) for m in metrics]
            leader = leader_verdict(estimates)
            row = {
                "key": key,
                "label": METRICS[key].label,
                "unit": values[0]["unit"],
                "values": values,
                "leader": {"index": leader.leader_index, "verdict": leader.verdict.value},
            }
            if len(player_seasons) == 2:
                row["pair_verdict"] = difference_verdict(estimates[0], estimates[1]).value
            rows.append(row)
        themes.append({
            "key": theme.value,
            "label": THEME_LABELS[theme],
            "possession_sensitive": theme in POSSESSION_SENSITIVE,
            "metrics": rows,
        })

    return {
        "players": [
            {
                "index": i,
                "player_id": ps["player_id"],
                "season_id": ps["season_id"],
                "name": ps["player_name"],
                "teams": ps["teams"],
                "competition": ps["competition"],
                "season_label": ps["season_label"],
                "position_group": ps.get("position_group"),
                "primary_role": ps.get("primary_role"),
                "minutes": ps["minutes"],
                "eligible": bool(ps["eligible"]),
                "team_possession_pct": ps.get("team_possession_pct"),
                "population_size": ps.get("population_group_size"),
            }
            for i, ps in enumerate(player_seasons)
        ],
        "same_position_group": same_group,
        "warnings": warnings,
        "themes": themes,
        "verdict_rule": "clear when |difference of regressed estimates| > 1.96 x combined posterior SD",
        "data_source": DATA_SOURCE,
    }


__all__ = ["MAX_PLAYERS", "MIN_PLAYERS", "build_comparison", "comparison_metrics", "DifferenceVerdict"]
