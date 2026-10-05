"""StatsBomb pitch units -> canonical metres (docs/data/STATSBOMB_MAPPING.md §2).

StatsBomb: 120 x 80 units, origin top-left, y grows downwards, every team
attacks left to right. Canonical: 105 x 68 m, origin bottom-left (D005).
"""

from __future__ import annotations

from collections.abc import Sequence

from football_platform.canonical.pitch import COORDINATE_DECIMALS, PITCH_LENGTH_M, PITCH_WIDTH_M, Point

STATSBOMB_LENGTH = 120.0
STATSBOMB_WIDTH = 80.0

# Locations up to this many StatsBomb units beyond a boundary are treated as
# recording noise and clamped onto the line. Anything further is a data error.
BOUNDARY_TOLERANCE_UNITS = 1.0


def _clamp(value: float, upper: float, raw: Sequence[float]) -> float:
    if value < -BOUNDARY_TOLERANCE_UNITS or value > upper + BOUNDARY_TOLERANCE_UNITS:
        raise ValueError(f"StatsBomb location {list(raw)!r} is outside the pitch")
    return min(max(value, 0.0), upper)


def to_canonical_point(location: Sequence[float] | None) -> Point | None:
    """Convert a StatsBomb [x, y] (or [x, y, z]) location; None stays None.

    Values within BOUNDARY_TOLERANCE_UNITS outside the pitch are clamped onto
    the touchline/goal line; values further out raise ValueError.
    """
    if location is None:
        return None
    if len(location) < 2:
        raise ValueError(f"Invalid StatsBomb location {location!r}")
    x = _clamp(location[0], STATSBOMB_LENGTH, location)
    y = _clamp(location[1], STATSBOMB_WIDTH, location)
    x_m = x / STATSBOMB_LENGTH * PITCH_LENGTH_M
    y_m = (STATSBOMB_WIDTH - y) / STATSBOMB_WIDTH * PITCH_WIDTH_M
    return Point(round(x_m, COORDINATE_DECIMALS), round(y_m, COORDINATE_DECIMALS))
