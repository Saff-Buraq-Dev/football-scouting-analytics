"""Assemble a player profile from snapshot rows (pure logic, no database).

Display rules: docs/FOOTBALL_ANALYTICS.md, "Phase 5 — Player profile".
"""

from __future__ import annotations

from typing import Any

from football_platform.analytics.definitions import ALL_METRICS, MetricKind, PositionGroup
from football_platform.analytics.profile_templates import POSSESSION_SENSITIVE, TEMPLATES, THEME_LABELS
from football_platform.api.report import highlights

METRICS = {m.key: m for m in ALL_METRICS}

# Display convention for the regressed-estimate weight w (Phase 5 doc).
HIGH_RELIABILITY = 0.8
MEDIUM_RELIABILITY = 0.5

DATA_SOURCE = {
    "provider": "StatsBomb Open Data",
    "notice": "Data: StatsBomb Open Data. Derived, aggregated metrics only; raw data is not redistributed.",
}


def reliability_band(weight: float | None) -> str | None:
    if weight is None:
        return None
    if weight >= HIGH_RELIABILITY:
        return "high"
    return "medium" if weight >= MEDIUM_RELIABILITY else "low"


def percentile_note(metric_key: str, row: dict[str, Any], eligible: bool) -> str | None:
    """Why a percentile is missing, if it is."""
    if row.get("percentile") is not None:
        return None
    if row.get("value") is None:
        return "unavailable"
    if not eligible:
        return "below_minutes_threshold"
    if METRICS[metric_key].kind is MetricKind.RATIO:
        return "insufficient_attempts"
    return "not_ranked"


def metric_view(metric_key: str, row: dict[str, Any] | None, eligible: bool) -> dict[str, Any]:
    spec = METRICS[metric_key]
    row = row or {}
    return {
        "key": metric_key,
        "label": spec.label,
        "kind": spec.kind.value,
        "unit": "per_90" if spec.kind is MetricKind.COUNT else "ratio",
        "value": row.get("value"),
        "total": row.get("total"),
        "percentile": row.get("percentile"),
        "percentile_note": percentile_note(metric_key, row, eligible),
        "regressed": row.get("regressed"),
        "reliability": row.get("reliability"),
        "reliability_band": reliability_band(row.get("reliability")),
    }


def build_profile(player_season: dict[str, Any], metrics: dict[str, dict[str, Any]],
                  min_minutes: float) -> dict[str, Any]:
    """player_season: snapshot row joined with names; metrics: metric_key -> metric row."""
    eligible = bool(player_season["eligible"])
    group = player_season.get("position_group")
    template = TEMPLATES.get(PositionGroup(group), {}) if group else {}
    themes = [
        {
            "key": theme.value,
            "label": THEME_LABELS[theme],
            "possession_sensitive": theme in POSSESSION_SENSITIVE,
            "metrics": [metric_view(k, metrics.get(k), eligible) for k in keys],
        }
        for theme, keys in template.items()
    ]
    return {
        "player": {"id": player_season["player_id"], "name": player_season["player_name"],
                   "nationality": player_season.get("nationality")},
        "season": {"id": player_season["season_id"], "label": player_season["season_label"],
                   "competition": player_season["competition"]},
        "teams": player_season["teams"],
        "playing_time": {
            "minutes": player_season["minutes"],
            "appearances": player_season["appearances"],
            "starts": player_season["starts"],
            "primary_role": player_season.get("primary_role"),
            "primary_role_share": player_season.get("primary_role_share"),
            "position_group": group,
            "eligible": eligible,
            "min_minutes": min_minutes,
        },
        "context": {"team_possession_pct": player_season.get("team_possession_pct")},
        "population": {
            "position_group": group,
            "size": player_season.get("population_group_size", player_season.get("population_size")),
            "seasons": player_season.get("population_seasons", []),
            "min_minutes": min_minutes,
        },
        "themes": themes,
        "highlights": highlights(themes),
        "all_metrics": [metric_view(k, metrics.get(k), eligible) for k in METRICS],
        "data_source": DATA_SOURCE,
    }
