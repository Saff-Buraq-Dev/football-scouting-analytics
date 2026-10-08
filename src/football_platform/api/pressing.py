"""Team pressing maps: zone aggregates of defensive actions and ball wins (Phase 11.3, D027)."""

from __future__ import annotations

from typing import Any

import pandas as pd

from football_platform.analytics.zone_maps import LAYOUT, ZONES, distribution, pressing_points, share
from football_platform.api.profile import DATA_SOURCE

COLUMNS = ["type", "outcome", "duel_kind", "period", "start_x", "start_y"]
MAPS = {
    "defensive_actions": "Tackles, interceptions, ball recoveries and fouls",
    "ball_wins": "Tackles won, interceptions and successful recoveries",
}


def _frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=COLUMNS)
    df[["start_x", "start_y"]] = df[["start_x", "start_y"]].astype(float)
    return df


def counts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {key: distribution(p["x"], p["y"]) for key, p in pressing_points(_frame(rows)).items()}


def build_pressing_maps(team_rows: list[dict[str, Any]], league_counts: dict[str, Any]) -> dict[str, Any]:
    team = counts(team_rows)
    maps = []
    for key, description in MAPS.items():
        own, league = share(team[key]), share(league_counts[key])
        maps.append({
            "key": key, "description": description, "total": int(team[key].sum()),
            "zones": [{"index": i, "strip": i // len(LAYOUT.channels), "channel": LAYOUT.channels[i % len(LAYOUT.channels)],
                       "count": int(team[key][i]), "share": float(own[i]), "group_share": float(league[i])}
                      for i in range(ZONES)],
        })
    return {
        "layout": {"strip_edges": LAYOUT.strip_edges, "channel_edges": LAYOUT.channel_edges, "channels": list(LAYOUT.channels)},
        "baseline": "league average",
        "maps": maps,
        "data_source": DATA_SOURCE,
    }
