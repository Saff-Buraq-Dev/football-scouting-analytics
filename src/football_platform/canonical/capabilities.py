"""What a data source can deliver (docs/ARCHITECTURE.md §3).

Lives in the canonical layer because analytics must check it ("unavailable"
is not "zero") without depending on any provider package.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class PositionGranularity(StrEnum):
    SLOT = "slot"  # line, role and side (e.g. "Left Center Back")
    LINE = "line"  # only GK / DEF / MID / FWD


class TimePrecision(StrEnum):
    SECOND = "second"
    MINUTE = "minute"


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    provider: str
    source_coordinate_system: str
    has_event_end_locations: bool
    has_provider_xg: bool
    has_pressure_events: bool
    has_carries: bool
    has_ball_receipts: bool
    has_freeze_frames: bool
    has_possession_ids: bool
    has_player_birth_date: bool
    has_position_spells: bool
    position_granularity: PositionGranularity
    minutes_precision: TimePrecision

    def to_dict(self) -> dict[str, Any]:
        return {k: (v.value if isinstance(v, StrEnum) else v) for k, v in asdict(self).items()}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProviderCapabilities":
        values = dict(data)
        values["position_granularity"] = PositionGranularity(values["position_granularity"])
        values["minutes_precision"] = TimePrecision(values["minutes_precision"])
        return cls(**values)
