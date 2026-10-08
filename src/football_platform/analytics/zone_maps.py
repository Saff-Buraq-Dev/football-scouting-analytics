"""Player zone maps: touches, receptions and ball progression (docs/FOOTBALL_ANALYTICS.md, Phase 11.2).

Zones: 6 strips along the pitch × 5 channels across it. Channel boundaries follow the pitch
markings (penalty-box and six-yard-box lines), the frame coaches use for wings, half-spaces and centre.
Canonical y = 68 is the attacking team's left (docs/ARCHITECTURE.md §4.2).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from football_platform.analytics.definitions import GOAL_Y, PENALTY_AREA_HALF_WIDTH_M
from football_platform.analytics.geometry import is_progressive
from football_platform.canonical.enums import EventType, Outcome
from football_platform.canonical.models import SHOOTOUT_PERIOD
from football_platform.canonical.pitch import PITCH_LENGTH_M, PITCH_WIDTH_M

SIX_YARD_HALF_WIDTH_M = 18.32 / 2
STRIPS = 6
# Channel edges from right (y = 0) to left (y = 68): right wing | right half-space | centre | left half-space | left wing
CHANNEL_EDGES = np.array([
    0.0,
    GOAL_Y - PENALTY_AREA_HALF_WIDTH_M,  # 13.84: penalty-box line
    GOAL_Y - SIX_YARD_HALF_WIDTH_M,      # 24.84: six-yard-box line
    GOAL_Y + SIX_YARD_HALF_WIDTH_M,      # 43.16
    GOAL_Y + PENALTY_AREA_HALF_WIDTH_M,  # 54.16
    PITCH_WIDTH_M,
])
CHANNELS = ("right_wing", "right_half_space", "centre", "left_half_space", "left_wing")
ZONES = STRIPS * len(CHANNELS)

# On-ball actions available from any event provider (carries and ball receipts are StatsBomb-specific).
TOUCH_TYPES = {
    EventType.PASS.value, EventType.SHOT.value, EventType.TAKE_ON.value, EventType.BALL_RECOVERY.value,
    EventType.INTERCEPTION.value, EventType.CLEARANCE.value, EventType.MISCONTROL.value, EventType.DISPOSSESSED.value,
}


@dataclass(frozen=True, slots=True)
class ZoneLayout:
    strip_edges: list[float]
    channel_edges: list[float]
    channels: tuple[str, ...]


LAYOUT = ZoneLayout(
    strip_edges=list(np.linspace(0.0, PITCH_LENGTH_M, STRIPS + 1)),
    channel_edges=list(CHANNEL_EDGES),
    channels=CHANNELS,
)


def zone_index(x: pd.Series, y: pd.Series) -> np.ndarray:
    """strip * 5 + channel (strip 0 = own goal end, channel 0 = right wing); -1 if missing."""
    x_arr, y_arr = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    strip = np.clip(np.floor(x_arr / PITCH_LENGTH_M * STRIPS), 0, STRIPS - 1)
    channel = np.clip(np.searchsorted(CHANNEL_EDGES, y_arr, side="right") - 1, 0, len(CHANNELS) - 1)
    return np.where(np.isnan(x_arr) | np.isnan(y_arr), -1, strip * len(CHANNELS) + channel).astype(int)


def distribution(x: pd.Series, y: pd.Series) -> np.ndarray:
    zones = zone_index(x, y)
    return np.bincount(zones[zones >= 0], minlength=ZONES).astype(float)


def touches(events: pd.DataFrame) -> pd.DataFrame:
    """The player's own on-ball actions (start locations), shoot-out excluded."""
    ev = events[(events["period"] != SHOOTOUT_PERIOD) & events["type"].isin(TOUCH_TYPES)]
    return ev[["start_x", "start_y"]].rename(columns={"start_x": "x", "start_y": "y"})


def receptions(passes_to_player: pd.DataFrame) -> pd.DataFrame:
    """Completed passes received by the player (end locations of teammates' passes)."""
    ok = passes_to_player[(passes_to_player["outcome"] == Outcome.SUCCESS.value)
                          & (passes_to_player["period"] != SHOOTOUT_PERIOD)]
    return ok[["end_x", "end_y"]].rename(columns={"end_x": "x", "end_y": "y"})


def progression(events: pd.DataFrame) -> pd.DataFrame:
    """Destinations of the player's progressive actions: completed open-play passes, and carries."""
    ev = events[(events["period"] != SHOOTOUT_PERIOD) & events["set_piece"].isna()]
    completed_pass = (ev["type"] == EventType.PASS.value) & (ev["outcome"] == Outcome.SUCCESS.value)
    carry = ev["type"] == EventType.CARRY.value
    candidate = ev[completed_pass | carry]
    progressive = is_progressive(candidate["start_x"].astype(float), candidate["start_y"].astype(float),
                                 candidate["end_x"].astype(float), candidate["end_y"].astype(float))
    chosen = candidate[progressive.to_numpy()]
    return chosen[["end_x", "end_y"]].rename(columns={"end_x": "x", "end_y": "y"})


def share(counts: np.ndarray) -> np.ndarray:
    total = counts.sum()
    return counts / total if total else counts
