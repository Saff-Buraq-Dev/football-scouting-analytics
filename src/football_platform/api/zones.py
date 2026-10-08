"""Player zone maps: zone aggregates only, never individual events (D004). Method: Phase 11.2."""

from __future__ import annotations

from typing import Any

import pandas as pd

from football_platform.analytics.zone_maps import (
    LAYOUT,
    ZONES,
    distribution,
    progression,
    receptions,
    share,
    touches,
)
from football_platform.api.profile import DATA_SOURCE

COLUMNS = ["period", "type", "outcome", "set_piece", "start_x", "start_y", "end_x", "end_y"]
MAPS = {
    "touches": "On-ball actions (passes, shots, take-ons, recoveries, interceptions, clearances, losses)",
    "receptions": "Completed passes received",
    "progression": "Where his progressive passes and carries end",
}


def frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=COLUMNS)
    for column in ("start_x", "start_y", "end_x", "end_y"):
        df[column] = df[column].astype(float)
    return df


def map_counts(own: pd.DataFrame, received: pd.DataFrame) -> dict[str, Any]:
    points = {"touches": touches(own), "receptions": receptions(received), "progression": progression(own)}
    return {key: distribution(p["x"], p["y"]) for key, p in points.items()}


def build_zone_maps(own_rows, received_rows, group_counts: dict[str, Any], position_group: str | None) -> dict[str, Any]:
    counts = map_counts(frame(own_rows), frame(received_rows))
    maps = []
    for key, description in MAPS.items():
        player_share, group_share = share(counts[key]), share(group_counts[key])
        maps.append({
            "key": key,
            "description": description,
            "total": int(counts[key].sum()),
            "zones": [
                {"index": i, "strip": i // len(LAYOUT.channels), "channel": LAYOUT.channels[i % len(LAYOUT.channels)],
                 "count": int(counts[key][i]), "share": float(player_share[i]), "group_share": float(group_share[i])}
                for i in range(ZONES)
            ],
        })
    return {
        "layout": {"strip_edges": LAYOUT.strip_edges, "channel_edges": LAYOUT.channel_edges, "channels": list(LAYOUT.channels)},
        "position_group": position_group,
        "maps": maps,
        "data_source": DATA_SOURCE,
    }
