"""Corner analysis (docs/FOOTBALL_ANALYTICS.md, Phase 11.6).

Corners are mirrored so the taker is always on the attacker's left (y ≈ 68), then classified by
delivery zone. Outcomes are the shots of the possession the corner starts (needs possession ids).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from football_platform.analytics.definitions import GOAL_Y, PENALTY_AREA_HALF_WIDTH_M, PENALTY_AREA_X
from football_platform.canonical.enums import EventType, SetPiece, ShotOutcome
from football_platform.canonical.models import SHOOTOUT_PERIOD
from football_platform.canonical.pitch import PITCH_WIDTH_M

SIX_YARD_X = 105.0 - 5.5
SIX_YARD_HALF_WIDTH_M = 18.32 / 2


@dataclass(frozen=True, slots=True)
class DeliveryZone:
    key: str
    label: str


DELIVERY_ZONES: tuple[DeliveryZone, ...] = (
    DeliveryZone("short", "Short or outside the box"),
    DeliveryZone("six_yard_near", "Six-yard box, near post"),
    DeliveryZone("six_yard_far", "Six-yard box, far post"),
    DeliveryZone("penalty_spot", "Penalty-spot area"),
    DeliveryZone("box_near_side", "Box, near side"),
    DeliveryZone("box_far_side", "Box, far side"),
)
ZONE_KEYS = [z.key for z in DELIVERY_ZONES]


def delivery_zone(start_y: pd.Series, end_x: pd.Series, end_y: pd.Series) -> pd.Series:
    """Delivery zone of each corner, after mirroring so the taker is on the attacker's left (y = 68)."""
    mirror = start_y < GOAL_Y
    y = np.where(mirror, PITCH_WIDTH_M - end_y, end_y)  # near side = y > 34 after mirroring
    x = np.asarray(end_x, dtype=float)
    lateral = y - GOAL_Y
    in_box = (x >= PENALTY_AREA_X) & (np.abs(lateral) <= PENALTY_AREA_HALF_WIDTH_M)
    zone = np.select(
        [
            ~in_box | np.isnan(x),
            (x >= SIX_YARD_X) & (np.abs(lateral) <= SIX_YARD_HALF_WIDTH_M) & (lateral >= 0),
            (x >= SIX_YARD_X) & (np.abs(lateral) <= SIX_YARD_HALF_WIDTH_M),
            np.abs(lateral) <= SIX_YARD_HALF_WIDTH_M,
            lateral > 0,
        ],
        ["short", "six_yard_near", "six_yard_far", "penalty_spot", "box_near_side"],
        default="box_far_side",
    )
    return pd.Series(zone, index=end_x.index)


def corner_outcomes(events: pd.DataFrame, shot_xg: pd.Series) -> pd.DataFrame:
    """One row per corner: delivery zone, shots, xG and goals of the possession it starts.

    events: id, match_id, team_id, period, time_s, type, set_piece, start_y, end_x, end_y, shot_outcome,
    possession_id. Without possession ids, outcome columns are NaN (unavailable).
    """
    ev = events[events["period"] != SHOOTOUT_PERIOD]
    corners = ev[(ev["type"] == EventType.PASS.value) & (ev["set_piece"] == SetPiece.CORNER.value)].copy()
    # Outcome columns are computed here; ignore any that came with the input (e.g. an xg column from the DB).
    corners = corners.drop(columns=["shots", "xg", "goals"], errors="ignore")
    corners["zone"] = delivery_zone(corners["start_y"].astype(float), corners["end_x"].astype(float),
                                    corners["end_y"].astype(float))
    if ev["possession_id"].isna().all():
        corners[["shots", "xg", "goals"]] = np.nan
        return corners[["id", "match_id", "team_id", "zone", "shots", "xg", "goals"]]

    shots = ev[ev["type"] == EventType.SHOT.value].assign(xg=lambda d: d["id"].map(shot_xg).fillna(0.0))
    keys = ["match_id", "team_id", "possession_id"]
    joined = corners[keys + ["id", "period", "time_s"]].merge(
        shots[keys + ["period", "time_s", "xg", "shot_outcome"]], on=keys, how="left", suffixes=("", "_shot"))
    after = (joined["period_shot"] > joined["period"]) | (
        (joined["period_shot"] == joined["period"]) & (joined["time_s_shot"] >= joined["time_s"]))
    joined = joined[after.fillna(False)]
    summary = joined.groupby("id").agg(
        shots=("xg", "size"), xg=("xg", "sum"),
        goals=("shot_outcome", lambda s: int((s == ShotOutcome.GOAL.value).sum())))
    corners = corners.merge(summary, left_on="id", right_index=True, how="left")
    corners[["shots", "xg", "goals"]] = corners[["shots", "xg", "goals"]].fillna(0.0)
    return corners[["id", "match_id", "team_id", "zone", "shots", "xg", "goals"]]


def corner_summary(corners: pd.DataFrame, matches: int) -> dict:
    """Totals and per-zone breakdown for a set of corners (one team's for/against, or a league)."""
    n = len(corners)
    available = corners["xg"].notna().any() if n else False
    zones = []
    for zone in DELIVERY_ZONES:
        sub = corners[corners["zone"] == zone.key]
        zones.append({
            "key": zone.key, "label": zone.label, "corners": int(len(sub)),
            "share": len(sub) / n if n else 0.0,
            "xg_per_corner": float(sub["xg"].mean()) if available and len(sub) else None,
            "shot_rate": float((sub["shots"] > 0).mean()) if available and len(sub) else None,
        })
    return {
        "corners": n,
        "per_match": n / matches if matches else None,
        "xg_per_corner": float(corners["xg"].mean()) if available and n else None,
        "shot_rate": float((corners["shots"] > 0).mean()) if available and n else None,
        "goals": int(corners["goals"].sum()) if available else None,
        "zones": zones,
    }
