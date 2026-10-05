"""Assemble team views (pure logic, no database). Method: docs/FOOTBALL_ANALYTICS.md, Phase 8."""

from __future__ import annotations

from typing import Any

from football_platform.analytics.team import TEAM_METRICS
from football_platform.api.profile import DATA_SOURCE

LABELS = {m.key: m.label for m in TEAM_METRICS}
RESULTS_METRICS = ("points_per_match", "xpts_per_match", "goal_diff_per_match", "npxg_diff_per_match",
                   "npxg_for_per_match", "npxg_against_per_match")
STYLE_METRICS = ("possession_pct", "ppda", "long_pass_share", "progressive_pass_share", "crosses_per_match",
                 "counter_npxg_share", "set_piece_npxg_share", "npxg_per_shot_for", "npxg_per_shot_against")
NOTES = {
    "ppda": "Lower = more intense pressing (fewer opponent passes allowed per defensive action).",
    "npxg_against_per_match": "Lower = fewer chances conceded.",
    "npxg_per_shot_against": "Lower = opponents get worse chances.",
    "set_piece_npxg_share": "Possessions starting from corners and free kicks; includes restarts that become open play.",
}


def metric_rows(keys: tuple[str, ...], metrics: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"key": k, "label": LABELS[k], "value": (metrics.get(k) or {}).get("value"),
         "percentile": (metrics.get(k) or {}).get("percentile"), "note": NOTES.get(k)}
        for k in keys
    ]


def team_list_item(team: dict[str, Any], metrics: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {**team, "metrics": {k: (metrics.get(k) or {}).get("value") for k in LABELS}}


def build_team_profile(team: dict[str, Any], metrics: dict[str, dict[str, Any]],
                       squad: list[dict[str, Any]]) -> dict[str, Any]:
    values = {k: (metrics.get(k) or {}).get("value") for k in LABELS}
    points, xpts = values.get("points_per_match"), values.get("xpts_per_match")
    return {
        "team": team,
        "results": metric_rows(RESULTS_METRICS, metrics),
        "points_vs_expected_per_match": None if points is None or xpts is None else points - xpts,
        "style": metric_rows(STYLE_METRICS, metrics),
        "squad": squad,
        "population": {"description": "percentiles within the team's league-season", "size": team.get("league_size")},
        "data_source": DATA_SOURCE,
    }
