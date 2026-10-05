"""Which metrics a player profile highlights for each position group.

Source of truth: docs/FOOTBALL_ANALYTICS.md, "Phase 5 — Player profile". The
tables there and here must stay identical (tests/analytics/test_profile_templates.py).
"""

from __future__ import annotations

from enum import StrEnum

from football_platform.analytics.definitions import PositionGroup


class Theme(StrEnum):
    SHOOTING = "shooting"
    CREATION = "creation"
    PROGRESSION = "progression"
    DEFENDING = "defending"
    AERIAL = "aerial"
    GOALKEEPING = "goalkeeping"


THEME_LABELS = {
    Theme.SHOOTING: "Shooting",
    Theme.CREATION: "Chance creation",
    Theme.PROGRESSION: "Ball progression",
    Theme.DEFENDING: "Defending",
    Theme.AERIAL: "Aerial duels",
    Theme.GOALKEEPING: "Goalkeeping",
}

G = PositionGroup
T = Theme

TEMPLATES: dict[PositionGroup, dict[Theme, tuple[str, ...]]] = {
    G.STRIKER: {
        T.SHOOTING: ("npxg", "np_shots", "npxg_per_shot", "np_goals"),
        T.CREATION: ("xa", "key_passes", "passes_into_box"),
        T.PROGRESSION: ("progressive_carries",),
        T.DEFENDING: ("pressures",),
        T.AERIAL: ("aerials_won", "aerial_win_pct"),
    },
    G.ATTACKING_MIDFIELD_WINGER: {
        T.SHOOTING: ("npxg", "np_shots", "np_goals"),
        T.CREATION: ("xa", "key_passes", "passes_into_box", "assists"),
        T.PROGRESSION: ("progressive_passes", "progressive_carries", "passes_into_final_third"),
        T.DEFENDING: ("pressures", "tackles"),
    },
    G.CENTRAL_MIDFIELD: {
        T.SHOOTING: ("npxg",),
        T.CREATION: ("xa", "key_passes"),
        T.PROGRESSION: ("progressive_passes", "progressive_carries", "passes_into_final_third", "pass_completion"),
        T.DEFENDING: ("tackles", "interceptions", "ball_recoveries", "pressures"),
    },
    G.FULL_BACK: {
        T.CREATION: ("xa", "key_passes"),
        T.PROGRESSION: ("progressive_passes", "progressive_carries", "passes_into_final_third"),
        T.DEFENDING: ("tackles", "interceptions", "pressures"),
        T.AERIAL: ("aerial_win_pct",),
    },
    G.CENTRE_BACK: {
        T.PROGRESSION: ("progressive_passes", "pass_completion"),
        T.DEFENDING: ("interceptions", "tackles", "ball_recoveries"),
        T.AERIAL: ("aerials_won", "aerial_win_pct"),
    },
    G.GOALKEEPER: {
        T.GOALKEEPING: ("gk_np_save_pct", "gk_np_sot_faced", "gk_claims", "gk_sweeper_actions"),
        T.PROGRESSION: ("long_pass_share", "pass_completion"),
    },
}

# Themes whose values depend on how often the team was without the ball (D017):
# the profile shows team possession next to them.
POSSESSION_SENSITIVE = frozenset({Theme.DEFENDING})
