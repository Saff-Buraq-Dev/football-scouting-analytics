"""Single-match analysis: xG race, passing networks (docs/FOOTBALL_ANALYTICS.md, Phase 11.4-11.5)."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from football_platform.canonical.enums import CardType, EventType, Outcome, ShotOutcome
from football_platform.canonical.models import SHOOTOUT_PERIOD

XG_BIN_MINUTES = 5  # xG is shown per 5-minute bin, never shot by shot (D004)
MIN_EDGE_PASSES = 3  # passing-network links below this are hidden (too few to be a pattern)
# Below this, a network rests on too little play to read (6.9 % of team-matches, Phase 11.5 validation).
SMALL_NETWORK_PASSES = 100
DISMISSALS = {CardType.RED.value, CardType.SECOND_YELLOW.value}


def period_lengths(events: pd.DataFrame) -> dict[int, float]:
    """Actual length (s) of each played period, from period-end events."""
    ends = events[(events["type"] == EventType.PERIOD_END.value) & (events["period"] != SHOOTOUT_PERIOD)]
    return ends.groupby("period")["time_s"].max().to_dict()


def elapsed_minutes(period: pd.Series, time_s: pd.Series, lengths: dict[int, float]) -> pd.Series:
    """Minutes of actual play since kick-off (first-half stoppage time does not overlap the second half)."""
    offset = {p: sum(v for q, v in lengths.items() if q < p) for p in lengths}
    return (period.map(offset).fillna(0.0) + time_s) / 60.0


def xg_race(shots: pd.DataFrame, own_goals: pd.DataFrame, lengths: dict[int, float],
            home_id: str, away_id: str) -> list[dict[str, float]]:
    """Cumulative xG per team at the end of every 5-minute bin, and goals scored in each bin.

    shots: team_id, period, time_s, xg, shot_outcome (shoot-out excluded by the caller).
    own_goals: team_id (the conceding player's team), period, time_s.
    """
    total = sum(lengths.values()) / 60.0
    edges = np.arange(XG_BIN_MINUTES, math.ceil(total / XG_BIN_MINUTES) * XG_BIN_MINUTES + XG_BIN_MINUTES,
                      XG_BIN_MINUTES, dtype=float)
    minute = elapsed_minutes(shots["period"], shots["time_s"], lengths)
    og_minute = elapsed_minutes(own_goals["period"], own_goals["time_s"], lengths)
    bins = []
    for end in edges:
        start = end - XG_BIN_MINUTES
        row: dict[str, float] = {"minute": float(min(end, total))}
        for side, team, opponent in (("home", home_id, away_id), ("away", away_id, home_id)):
            mine = shots["team_id"] == team
            row[f"{side}_xg"] = float(shots.loc[mine & (minute <= end), "xg"].fillna(0.0).sum())
            in_bin = (minute > start) & (minute <= end)
            goals = int((mine & in_bin & (shots["shot_outcome"] == ShotOutcome.GOAL.value)).sum())
            goals += int(((own_goals["team_id"] == opponent) & (og_minute > start) & (og_minute <= end)).sum())
            row[f"{side}_goals"] = goals
        bins.append(row)
    return bins


@dataclass(frozen=True, slots=True)
class NetworkCutoff:
    minute: float
    reason: str


def network_cutoff(team_events: pd.DataFrame, lengths: dict[int, float]) -> NetworkCutoff:
    """Networks use the starting XI until the team's first substitution or dismissal."""
    changes = team_events[
        (team_events["type"] == EventType.SUBSTITUTION.value)
        | ((team_events["type"] == EventType.CARD.value) & team_events["card_type"].isin(DISMISSALS))
    ]
    changes = changes[changes["period"] != SHOOTOUT_PERIOD]
    if changes.empty:
        return NetworkCutoff(sum(lengths.values()) / 60.0, "full match")
    minutes = elapsed_minutes(changes["period"], changes["time_s"], lengths)
    first = minutes.idxmin()
    reason = "first substitution" if changes.loc[first, "type"] == EventType.SUBSTITUTION.value else "first dismissal"
    return NetworkCutoff(float(minutes.min()), reason)


def passing_network(team_events: pd.DataFrame, lengths: dict[int, float]) -> dict:
    """Average positions and completed-pass links of a team, before its first change.

    Node position = mean of the player's pass origins and pass receptions (canonical metres).
    Node size = completed passes made + received. Links: completed passes between two players
    (both directions), shown from MIN_EDGE_PASSES.
    """
    cutoff = network_cutoff(team_events, lengths)
    minute = elapsed_minutes(team_events["period"], team_events["time_s"], lengths)
    passes = team_events[
        (team_events["type"] == EventType.PASS.value) & (team_events["outcome"] == Outcome.SUCCESS.value)
        & team_events["pass_recipient_id"].notna() & team_events["player_id"].notna()
        & (minute <= cutoff.minute) & (team_events["period"] != SHOOTOUT_PERIOD)
    ]
    origins = passes[["player_id", "start_x", "start_y"]].rename(columns={"start_x": "x", "start_y": "y"})
    receptions = passes[["pass_recipient_id", "end_x", "end_y"]].rename(
        columns={"pass_recipient_id": "player_id", "end_x": "x", "end_y": "y"})
    points = pd.concat([origins, receptions], ignore_index=True).dropna()
    nodes = points.groupby("player_id").agg(x=("x", "mean"), y=("y", "mean"), involvement=("x", "size")).reset_index()

    pairs = passes.apply(lambda r: tuple(sorted((r["player_id"], r["pass_recipient_id"]))), axis=1) \
        if len(passes) else pd.Series([], dtype=object)
    edges = pairs.value_counts()
    links = [{"a": a, "b": b, "passes": int(n)} for (a, b), n in edges.items() if n >= MIN_EDGE_PASSES]
    return {
        "cutoff_minute": cutoff.minute,
        "cutoff_reason": cutoff.reason,
        "completed_passes": int(len(passes)),
        "small_sample": bool(len(passes) < SMALL_NETWORK_PASSES),
        "nodes": nodes.to_dict("records"),
        "links": links,
    }
