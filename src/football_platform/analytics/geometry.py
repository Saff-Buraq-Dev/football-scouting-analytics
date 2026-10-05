"""Pitch geometry on canonical coordinates (vectorised: works on floats and pandas Series)."""

from __future__ import annotations

from typing import TypeVar

import numpy as np
import pandas as pd

from football_platform.analytics.definitions import (
    GOAL_X,
    GOAL_Y,
    HALFWAY_X,
    PENALTY_AREA_HALF_WIDTH_M,
    PENALTY_AREA_X,
    PROGRESSIVE_GAIN_CROSSING_HALF_M,
    PROGRESSIVE_GAIN_OPPONENT_HALF_M,
    PROGRESSIVE_GAIN_OWN_HALF_M,
)

T = TypeVar("T")


def distance_to_goal(x: T, y: T) -> T:
    """Euclidean distance (m) to the centre of the goal being attacked."""
    return np.hypot(GOAL_X - x, GOAL_Y - y)  # type: ignore[return-value]


def in_penalty_area(x: T, y: T) -> T:
    return (x >= PENALTY_AREA_X) & (np.abs(y - GOAL_Y) <= PENALTY_AREA_HALF_WIDTH_M)  # type: ignore[return-value]


def is_progressive(start_x: T, start_y: T, end_x: T, end_y: T) -> T:
    """Wyscout-style progressive action (docs/FOOTBALL_ANALYTICS.md, "Ball progression").

    The ball must get closer to goal by 30 m (own half -> own half), 15 m
    (own half -> opponent half) or 10 m (opponent half -> opponent half).
    Missing coordinates give False.
    """
    gain = distance_to_goal(start_x, start_y) - distance_to_goal(end_x, end_y)
    starts_own_half = start_x < HALFWAY_X
    ends_own_half = end_x < HALFWAY_X
    required = np.where(
        starts_own_half & ends_own_half,
        PROGRESSIVE_GAIN_OWN_HALF_M,
        np.where(starts_own_half, PROGRESSIVE_GAIN_CROSSING_HALF_M, PROGRESSIVE_GAIN_OPPONENT_HALF_M),
    )
    result = np.nan_to_num(gain, nan=-np.inf) >= required
    if isinstance(start_x, pd.Series):
        return pd.Series(result, index=start_x.index)  # type: ignore[return-value]
    return bool(result)  # type: ignore[return-value]
