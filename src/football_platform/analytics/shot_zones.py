"""Shot zones (docs/FOOTBALL_ANALYTICS.md, "Phase 9b — Shot zone maps")."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from football_platform.analytics.definitions import GOAL_Y, PENALTY_AREA_HALF_WIDTH_M, PENALTY_AREA_X, PITCH_LENGTH_M
from football_platform.canonical.enums import SetPiece, ShotOutcome
from football_platform.canonical.models import SHOOTOUT_PERIOD

SIX_YARD_DEPTH_M = 5.5  # Laws of the Game
SIX_YARD_HALF_WIDTH_M = 18.32 / 2
SIX_YARD_X = PITCH_LENGTH_M - SIX_YARD_DEPTH_M
EDGE_OF_BOX_X = PITCH_LENGTH_M - 25.0  # analytics convention: 25 m from goal


@dataclass(frozen=True, slots=True)
class Zone:
    key: str
    label: str


ZONES: tuple[Zone, ...] = (
    Zone("six_yard", "Six-yard box"),
    Zone("box_central", "Box, central"),
    Zone("box_wide", "Box, wide"),
    Zone("edge", "Edge of the box"),
    Zone("outside_wide", "Outside, wide"),
    Zone("long_range", "Long range"),
)
ZONE_KEYS = [z.key for z in ZONES]


def classify(x: pd.Series, y: pd.Series) -> pd.Series:
    """Zone key for each shot location (canonical metres)."""
    lateral = np.abs(y - GOAL_Y)
    in_box = (x >= PENALTY_AREA_X) & (lateral <= PENALTY_AREA_HALF_WIDTH_M)
    zone = np.select(
        [
            (x >= SIX_YARD_X) & (lateral <= SIX_YARD_HALF_WIDTH_M),
            in_box & (lateral <= SIX_YARD_HALF_WIDTH_M),
            in_box,
            (x >= EDGE_OF_BOX_X) & (lateral <= PENALTY_AREA_HALF_WIDTH_M),
            x >= EDGE_OF_BOX_X,
        ],
        ["six_yard", "box_central", "box_wide", "edge", "outside_wide"],
        default="long_range",
    )
    return pd.Series(zone, index=x.index)


def prepare_shots(shots: pd.DataFrame) -> pd.DataFrame:
    """shots: id, period, start_x, start_y, set_piece, shot_outcome, xg. Returns open/set-play
    non-penalty shots (shoot-out excluded) with `zone` and `goal` columns."""
    s = shots[(shots["period"] != SHOOTOUT_PERIOD) & (shots["set_piece"] != SetPiece.PENALTY.value)].copy()
    s = s[s["start_x"].notna() & s["start_y"].notna()]
    s["zone"] = classify(s["start_x"].astype(float), s["start_y"].astype(float))
    s["goal"] = s["shot_outcome"] == ShotOutcome.GOAL.value
    return s


def zone_summary(shots: pd.DataFrame) -> pd.DataFrame:
    """Per zone: shots, goals, npxg, npxg_per_shot, share of shots. All six zones always present."""
    grouped = shots.groupby("zone").agg(shots=("zone", "size"), goals=("goal", "sum"), npxg=("xg", "sum"))
    summary = grouped.reindex(ZONE_KEYS, fill_value=0)
    summary["npxg_per_shot"] = summary["npxg"] / summary["shots"].replace(0, np.nan)
    total = summary["shots"].sum()
    summary["share"] = summary["shots"] / total if total else 0.0
    return summary.reset_index(names="zone")


def penalty_summary(shots: pd.DataFrame) -> dict[str, int]:
    pens = shots[(shots["period"] != SHOOTOUT_PERIOD) & (shots["set_piece"] == SetPiece.PENALTY.value)]
    return {"taken": int(len(pens)), "scored": int((pens["shot_outcome"] == ShotOutcome.GOAL.value).sum())}
