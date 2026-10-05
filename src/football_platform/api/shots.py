"""Shot zone maps: aggregated shots per zone only, never individual shots (D004, D023)."""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from football_platform.analytics.shot_zones import ZONES, penalty_summary, prepare_shots, zone_summary
from football_platform.api.profile import DATA_SOURCE

LABELS = {z.key: z.label for z in ZONES}
COLUMNS = ["id", "period", "start_x", "start_y", "set_piece", "shot_outcome", "xg"]


def _frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=COLUMNS)


def _num(value: float) -> float | None:
    return None if value is None or (isinstance(value, float) and math.isnan(value)) else float(value)


def zones_view(rows: list[dict[str, Any]], baseline_rows: list[dict[str, Any]]) -> dict[str, Any]:
    shots = _frame(rows)
    summary = zone_summary(prepare_shots(shots)).set_index("zone")
    baseline = zone_summary(prepare_shots(_frame(baseline_rows))).set_index("zone")
    zones = [
        {
            "key": key,
            "label": LABELS[key],
            "shots": int(row["shots"]),
            "goals": int(row["goals"]),
            "npxg": float(row["npxg"]),
            "npxg_per_shot": _num(row["npxg_per_shot"]),
            "share": float(row["share"]),
            "baseline_share": float(baseline.loc[key, "share"]),
            "baseline_npxg_per_shot": _num(baseline.loc[key, "npxg_per_shot"]),
        }
        for key, row in summary.iterrows()
    ]
    return {
        "zones": zones,
        "totals": {"shots": int(summary["shots"].sum()), "goals": int(summary["goals"].sum()),
                   "npxg": float(summary["npxg"].sum())},
        "penalties": penalty_summary(shots),
    }


def player_shot_map(rows, baseline_rows, baseline_label: str) -> dict[str, Any]:
    return {**zones_view(rows, baseline_rows), "baseline": baseline_label, "data_source": DATA_SOURCE}


def team_shot_map(for_rows, against_rows, league_rows) -> dict[str, Any]:
    return {
        "for": zones_view(for_rows, league_rows),
        "against": zones_view(against_rows, league_rows),
        "baseline": "league average",
        "data_source": DATA_SOURCE,
    }
