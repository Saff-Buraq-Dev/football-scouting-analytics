"""Archetype views (Phase 11.7, D030). Types are described by computed statistics, never named by hand."""

from __future__ import annotations

from typing import Any

from football_platform.analytics.archetypes import ALSO_CLOSE_RATIO
from football_platform.analytics.definitions import ALL_METRICS
from football_platform.api.profile import DATA_SOURCE

LABELS = {m.key: m.label for m in ALL_METRICS}
NOTE = (
    "Types come from clustering profile shapes (what a player does relatively more or less, volume removed) "
    "within the position group. They are tendencies: in a half-season test, type membership was only "
    "moderately stable (adjusted Rand index 0.2–0.35). Players close to two types are shown as such."
)


def type_view(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "index": row["archetype_index"],
        "size": row["size"],
        "more": [LABELS.get(k, k) for k in row["more_features"]],
        "less": [LABELS.get(k, k) for k in row["less_features"]],
        "prototypes": row["prototypes"] or [],
    }


def overview(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(row["position_group"], []).append(type_view(row))
    return {"groups": groups, "note": NOTE, "data_source": DATA_SOURCE}


def player_view(assignment: dict[str, Any] | None, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if assignment is None:
        return None
    types = {r["archetype_index"]: type_view(r) for r in rows if r["position_group"] == assignment["position_group"]}
    second = assignment.get("second_index")
    also_close = (second is not None and assignment["second_distance"] / assignment["distance"] < ALSO_CLOSE_RATIO
                  if assignment["distance"] > 0 else False)
    return {
        "position_group": assignment["position_group"],
        "type": types[assignment["archetype_index"]],
        "also_close_to": types[second] if also_close else None,
        "types_in_group": len(types),
        "note": NOTE,
    }
