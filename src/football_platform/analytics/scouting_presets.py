"""Role presets: editable starting points for scouting filters, not models.

Source of truth: docs/FOOTBALL_ANALYTICS.md, "Phase 7 — Scouting", section 3.
"""

from __future__ import annotations

from dataclasses import dataclass

from football_platform.analytics.definitions import PositionGroup
from football_platform.analytics.scouting import Criterion


@dataclass(frozen=True, slots=True)
class RolePreset:
    key: str
    label: str
    position_group: PositionGroup
    intent: str
    criteria: tuple[Criterion, ...]


C = Criterion
G = PositionGroup

PRESETS: tuple[RolePreset, ...] = (
    RolePreset("ball_winning_midfielder", "Ball-winning midfielder", G.CENTRAL_MIDFIELD, "Wins the ball back",
               (C("tackles", 70), C("interceptions", 60), C("ball_recoveries", 60))),
    RolePreset("deep_lying_playmaker", "Deep-lying playmaker", G.CENTRAL_MIDFIELD, "Moves the ball forward from deep",
               (C("progressive_passes", 80), C("passes_into_final_third", 70), C("pass_completion", 60))),
    RolePreset("creative_winger", "Creative winger / AM", G.ATTACKING_MIDFIELD_WINGER,
               "Creates chances and carries the ball",
               (C("xa", 75), C("key_passes", 70), C("progressive_carries", 60))),
    RolePreset("goal_threat_striker", "Goal-threat striker", G.STRIKER, "Gets into scoring positions",
               (C("npxg", 75), C("np_shots", 70))),
    RolePreset("pressing_forward", "Pressing forward", G.STRIKER, "Defends from the front while still threatening",
               (C("pressures", 75), C("npxg", 50))),
    RolePreset("attacking_full_back", "Attacking full-back", G.FULL_BACK, "Contributes in the final third",
               (C("passes_into_final_third", 70), C("xa", 60), C("progressive_carries", 60))),
    RolePreset("ball_playing_centre_back", "Ball-playing centre-back", G.CENTRE_BACK,
               "Progresses play while defending",
               (C("progressive_passes", 75), C("pass_completion", 60), C("aerial_win_pct", 50))),
    RolePreset("sweeper_keeper", "Sweeper keeper", G.GOALKEEPER,
               "Defends space behind the line, takes part in build-up",
               (C("gk_sweeper_actions", 70), C("pass_completion", 50))),
)
