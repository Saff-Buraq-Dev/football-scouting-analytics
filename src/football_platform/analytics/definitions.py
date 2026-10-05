"""Analytical constants and the metric registry (docs/FOOTBALL_ANALYTICS.md, Phase 4).

Every number here is a documented methodological choice, not a magic number.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from football_platform.canonical.enums import PositionRole
from football_platform.canonical.pitch import PITCH_LENGTH_M, PITCH_WIDTH_M

# -- Sample size ----------------------------------------------------------------
DEFAULT_MIN_MINUTES = 900.0  # ~10 full matches; per-90 values below this are unstable

# -- Pitch geometry (canonical metres, attacking towards x = 105) -------------------
GOAL_X = PITCH_LENGTH_M
GOAL_Y = PITCH_WIDTH_M / 2
HALFWAY_X = PITCH_LENGTH_M / 2
FINAL_THIRD_X = PITCH_LENGTH_M * 2 / 3  # 70 m
PENALTY_AREA_DEPTH_M = 16.5  # Laws of the Game
PENALTY_AREA_HALF_WIDTH_M = 40.32 / 2  # 40.32 m wide (Laws of the Game)
PENALTY_AREA_X = PITCH_LENGTH_M - PENALTY_AREA_DEPTH_M  # 88.5 m

# -- Progressive actions (Wyscout-style definition) ----------------------------------
PROGRESSIVE_GAIN_OWN_HALF_M = 30.0  # start and end in own half
PROGRESSIVE_GAIN_CROSSING_HALF_M = 15.0  # from own half into opponent half
PROGRESSIVE_GAIN_OPPONENT_HALF_M = 10.0  # start and end in opponent half


# -- Position groups (reference populations for percentiles) ----------------------
class PositionGroup(StrEnum):
    GOALKEEPER = "goalkeeper"
    CENTRE_BACK = "centre_back"
    FULL_BACK = "full_back"
    CENTRAL_MIDFIELD = "central_midfield"
    ATTACKING_MIDFIELD_WINGER = "attacking_midfield_winger"
    STRIKER = "striker"


POSITION_GROUP_BY_ROLE: dict[PositionRole, PositionGroup] = {
    PositionRole.GK: PositionGroup.GOALKEEPER,
    PositionRole.CB: PositionGroup.CENTRE_BACK,
    PositionRole.FB: PositionGroup.FULL_BACK,
    PositionRole.WB: PositionGroup.FULL_BACK,
    PositionRole.DM: PositionGroup.CENTRAL_MIDFIELD,
    PositionRole.CM: PositionGroup.CENTRAL_MIDFIELD,
    PositionRole.AM: PositionGroup.ATTACKING_MIDFIELD_WINGER,
    PositionRole.WM: PositionGroup.ATTACKING_MIDFIELD_WINGER,
    PositionRole.W: PositionGroup.ATTACKING_MIDFIELD_WINGER,
    PositionRole.CF: PositionGroup.STRIKER,
}


# -- Distribution -------------------------------------------------------------------
LONG_PASS_M = 40.0


# -- Metric registry --------------------------------------------------------------
class MetricKind(StrEnum):
    COUNT = "count"  # reported as total and per 90
    RATIO = "ratio"  # numerator / denominator, no per-90


@dataclass(frozen=True, slots=True)
class MetricSpec:
    key: str
    label: str
    kind: MetricKind
    capability: str | None = None  # ProviderCapabilities flag required, if any
    numerator: str | None = None  # ratios only
    denominator: str | None = None  # ratios only
    min_denominator: int = 0  # ratios: ranked only above this (Phase 4.1 §1)
    position_groups: frozenset[str] | None = None  # None = every group
    regress: bool = False  # counts: produce a regressed estimate (Phase 4.1 §4)


GK_ONLY = frozenset({"goalkeeper"})

COUNT_METRICS: tuple[MetricSpec, ...] = (
    MetricSpec("np_shots", "Non-penalty shots", MetricKind.COUNT, regress=True),
    MetricSpec("np_goals", "Non-penalty goals", MetricKind.COUNT, regress=True),
    MetricSpec("penalty_goals", "Penalty goals", MetricKind.COUNT),
    MetricSpec("npxg", "Non-penalty xG", MetricKind.COUNT, capability="has_provider_xg", regress=True),
    MetricSpec("assists", "Assists", MetricKind.COUNT, regress=True),
    MetricSpec("key_passes", "Key passes", MetricKind.COUNT, regress=True),
    MetricSpec("xa", "xA (derived)", MetricKind.COUNT, capability="has_provider_xg", regress=True),
    MetricSpec("passes_attempted", "Passes attempted", MetricKind.COUNT),
    MetricSpec("passes_completed", "Passes completed", MetricKind.COUNT),
    MetricSpec("long_passes_attempted", "Long passes attempted", MetricKind.COUNT),
    MetricSpec("progressive_passes", "Progressive passes", MetricKind.COUNT, regress=True),
    MetricSpec("progressive_carries", "Progressive carries", MetricKind.COUNT, capability="has_carries", regress=True),
    MetricSpec("passes_into_final_third", "Passes into final third", MetricKind.COUNT, regress=True),
    MetricSpec("passes_into_box", "Passes into penalty area", MetricKind.COUNT, regress=True),
    MetricSpec("tackles", "Tackles", MetricKind.COUNT, regress=True),
    MetricSpec("tackles_won", "Tackles won", MetricKind.COUNT),
    MetricSpec("interceptions", "Interceptions", MetricKind.COUNT, regress=True),
    MetricSpec("ball_recoveries", "Ball recoveries", MetricKind.COUNT, regress=True),
    MetricSpec("pressures", "Pressures", MetricKind.COUNT, capability="has_pressure_events", regress=True),
    MetricSpec("aerials_won", "Aerial duels won", MetricKind.COUNT, regress=True),
    MetricSpec("aerials_lost", "Aerial duels lost", MetricKind.COUNT),
    MetricSpec("gk_np_sot_faced", "Shots on target faced (non-penalty)", MetricKind.COUNT, position_groups=GK_ONLY),
    MetricSpec("gk_np_goals_conceded", "Goals conceded (non-penalty)", MetricKind.COUNT, position_groups=GK_ONLY),
    MetricSpec("gk_np_saves", "Saves (non-penalty)", MetricKind.COUNT, position_groups=GK_ONLY),
    MetricSpec("gk_claims", "Claims and punches", MetricKind.COUNT, position_groups=GK_ONLY, regress=True),
    MetricSpec("gk_sweeper_actions", "Sweeper actions", MetricKind.COUNT, position_groups=GK_ONLY, regress=True),
)

RATIO_METRICS: tuple[MetricSpec, ...] = (
    MetricSpec("pass_completion", "Pass completion", MetricKind.RATIO,
               numerator="passes_completed", denominator="passes_attempted", min_denominator=100),
    MetricSpec("long_pass_share", "Long pass share", MetricKind.RATIO,
               numerator="long_passes_attempted", denominator="passes_attempted", min_denominator=100),
    MetricSpec("npxg_per_shot", "npxG per shot", MetricKind.RATIO, capability="has_provider_xg",
               numerator="npxg", denominator="np_shots", min_denominator=20),
    MetricSpec("aerial_win_pct", "Aerial win %", MetricKind.RATIO,
               numerator="aerials_won", denominator="aerials_total", min_denominator=30),
    MetricSpec("gk_np_save_pct", "Save % (non-penalty)", MetricKind.RATIO, numerator="gk_np_saves",
               denominator="gk_np_sot_faced", min_denominator=40, position_groups=GK_ONLY),
)

ALL_METRICS = COUNT_METRICS + RATIO_METRICS
