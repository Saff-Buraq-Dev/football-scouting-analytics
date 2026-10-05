"""Canonical pitch coordinate system (decision D005).

Metres on a standard 105 x 68 pitch. Origin at the bottom-left corner as seen
by the acting team, which always attacks towards x = PITCH_LENGTH_M.
Real pitch sizes vary, so distances are approximations.
"""

from __future__ import annotations

from dataclasses import dataclass

PITCH_LENGTH_M = 105.0
PITCH_WIDTH_M = 68.0

# Rounding absorbs float noise from unit conversion without implying false precision.
COORDINATE_DECIMALS = 2


@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.x <= PITCH_LENGTH_M and 0.0 <= self.y <= PITCH_WIDTH_M):
            raise ValueError(f"Point ({self.x}, {self.y}) is outside the canonical pitch")
