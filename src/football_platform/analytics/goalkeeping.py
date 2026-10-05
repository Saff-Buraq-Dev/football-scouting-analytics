"""Shots faced by goalkeepers (docs/FOOTBALL_ANALYTICS.md, Phase 4.1 §3).

Each opponent shot is attributed to the defending team's player who was on the
pitch in the GK role at that moment (canonical position spells), which works
for any provider with position spells.
"""

from __future__ import annotations

import pandas as pd

from football_platform.canonical.enums import EventType, PositionRole, SetPiece, ShotOutcome
from football_platform.canonical.models import SHOOTOUT_PERIOD

KEYS = ["match_id", "player_id", "team_id"]
ON_TARGET = {ShotOutcome.GOAL.value, ShotOutcome.SAVED.value}
GK_COLUMNS = ["gk_np_sot_faced", "gk_np_goals_conceded", "gk_np_saves"]


def goalkeeper_match_stats(
    events: pd.DataFrame, position_spells: pd.DataFrame, matches: pd.DataFrame
) -> pd.DataFrame:
    """Per (match, goalkeeper, team): non-penalty shots on target faced, goals conceded, saves."""
    shots = events[
        (events["type"] == EventType.SHOT.value)
        & (events["period"] != SHOOTOUT_PERIOD)
        & (events["set_piece"] != SetPiece.PENALTY.value)
        & events["shot_outcome"].isin(ON_TARGET)
    ][["id", "match_id", "team_id", "period", "time_s", "shot_outcome"]]

    sides = matches[["id", "home_team_id", "away_team_id"]].rename(columns={"id": "match_id"})
    shots = shots.merge(sides, on="match_id")
    shots["defending_team_id"] = shots["home_team_id"].where(
        shots["team_id"] == shots["away_team_id"], shots["away_team_id"]
    )

    keepers = position_spells[position_spells["role"] == PositionRole.GK.value][
        ["match_id", "team_id", "player_id", "period", "start_s", "end_s"]
    ].rename(columns={"team_id": "defending_team_id"})
    faced = shots.merge(keepers, on=["match_id", "defending_team_id", "period"])
    faced = faced[(faced["time_s"] >= faced["start_s"]) & (faced["time_s"] <= faced["end_s"])]
    # A shot exactly at a goalkeeper change could match two spells: attribute it once.
    faced = faced.drop_duplicates(subset="id")

    faced = faced.assign(
        gk_np_sot_faced=1,
        gk_np_goals_conceded=(faced["shot_outcome"] == ShotOutcome.GOAL.value).astype(int),
        gk_np_saves=(faced["shot_outcome"] == ShotOutcome.SAVED.value).astype(int),
    ).rename(columns={"defending_team_id": "team_id_gk"})
    stats = (
        faced.groupby(["match_id", "player_id", "team_id_gk"])[GK_COLUMNS].sum().reset_index()
        .rename(columns={"team_id_gk": "team_id"})
    )
    return stats[KEYS + GK_COLUMNS]
