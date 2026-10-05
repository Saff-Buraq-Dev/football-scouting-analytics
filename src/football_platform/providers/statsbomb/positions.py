"""StatsBomb position names -> canonical (line, role, side) (docs/data/STATSBOMB_MAPPING.md §5)."""

from __future__ import annotations

from football_platform.canonical.enums import PositionLine as L
from football_platform.canonical.enums import PositionRole as R
from football_platform.canonical.enums import Side as S
from football_platform.canonical.models import Position

POSITION_MAP: dict[str, Position] = {
    "Goalkeeper": Position(L.GK, R.GK, S.CENTRE),
    "Right Back": Position(L.DEF, R.FB, S.RIGHT),
    "Left Back": Position(L.DEF, R.FB, S.LEFT),
    "Right Center Back": Position(L.DEF, R.CB, S.RIGHT),
    "Left Center Back": Position(L.DEF, R.CB, S.LEFT),
    "Center Back": Position(L.DEF, R.CB, S.CENTRE),
    "Right Wing Back": Position(L.DEF, R.WB, S.RIGHT),
    "Left Wing Back": Position(L.DEF, R.WB, S.LEFT),
    "Right Defensive Midfield": Position(L.MID, R.DM, S.RIGHT),
    "Left Defensive Midfield": Position(L.MID, R.DM, S.LEFT),
    "Center Defensive Midfield": Position(L.MID, R.DM, S.CENTRE),
    "Right Center Midfield": Position(L.MID, R.CM, S.RIGHT),
    "Left Center Midfield": Position(L.MID, R.CM, S.LEFT),
    "Center Midfield": Position(L.MID, R.CM, S.CENTRE),
    "Right Midfield": Position(L.MID, R.WM, S.RIGHT),
    "Left Midfield": Position(L.MID, R.WM, S.LEFT),
    "Right Attacking Midfield": Position(L.MID, R.AM, S.RIGHT),
    "Left Attacking Midfield": Position(L.MID, R.AM, S.LEFT),
    "Center Attacking Midfield": Position(L.MID, R.AM, S.CENTRE),
    "Right Wing": Position(L.FWD, R.W, S.RIGHT),
    "Left Wing": Position(L.FWD, R.W, S.LEFT),
    "Center Forward": Position(L.FWD, R.CF, S.CENTRE),
    "Right Center Forward": Position(L.FWD, R.CF, S.RIGHT),
    "Left Center Forward": Position(L.FWD, R.CF, S.LEFT),
    "Secondary Striker": Position(L.FWD, R.CF, S.CENTRE),
}


def to_canonical_position(name: str) -> Position:
    try:
        return POSITION_MAP[name]
    except KeyError:
        raise ValueError(f"Unknown StatsBomb position {name!r}") from None
