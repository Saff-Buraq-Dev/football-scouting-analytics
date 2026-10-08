"""Team corner analysis: aggregates only (Phase 11.6, D029)."""

from __future__ import annotations

from typing import Any

import pandas as pd

from football_platform.analytics.set_pieces import corner_outcomes, corner_summary
from football_platform.api.profile import DATA_SOURCE


def season_corners(rows: list[dict[str, Any]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(corners with outcomes and opponents, team-match pairs) for a league-season."""
    ev = pd.DataFrame(rows)
    for column in ("id", "match_id", "team_id", "home_team_id", "away_team_id"):
        ev[column] = ev[column].astype(str)
    for column in ("time_s", "start_y", "end_x", "end_y", "xg"):
        ev[column] = ev[column].astype(float)
    xg = ev.loc[ev["type"] == "shot"].set_index("id")["xg"]
    corners = corner_outcomes(ev, xg)
    sides = ev.drop_duplicates("match_id")[["match_id", "home_team_id", "away_team_id"]]
    corners = corners.merge(sides, on="match_id")
    corners["opponent_id"] = corners["home_team_id"].where(corners["team_id"] == corners["away_team_id"],
                                                           corners["away_team_id"])
    pairs = pd.concat([sides.rename(columns={"home_team_id": "team_id"})[["match_id", "team_id"]],
                       sides.rename(columns={"away_team_id": "team_id"})[["match_id", "team_id"]]])
    return corners, pairs


def build_corner_report(corners: pd.DataFrame, pairs: pd.DataFrame, team_id: str) -> dict[str, Any]:
    matches = int(pairs.loc[pairs["team_id"] == team_id, "match_id"].nunique())
    league = corner_summary(corners, int(len(pairs)))  # per team-match
    return {
        "for": corner_summary(corners[corners["team_id"] == team_id], matches),
        "against": corner_summary(corners[corners["opponent_id"] == team_id], matches),
        "league": league,
        "notes": {
            "zones": "Corners are mirrored so the taker is always on the left; near post = taker's side.",
            "outcome": "Shots, xG and goals of the possession the corner starts.",
        },
        "data_source": DATA_SOURCE,
    }
