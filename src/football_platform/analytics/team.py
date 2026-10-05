"""Team-season analysis: results versus performance, and playing style.

Definitions: docs/FOOTBALL_ANALYTICS.md, "Phase 8 — Team analysis".
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from football_platform.analytics.definitions import LONG_PASS_M, PITCH_LENGTH_M
from football_platform.analytics.geometry import is_progressive
from football_platform.analytics.player_match import shot_xg
from football_platform.canonical.capabilities import ProviderCapabilities
from football_platform.canonical.enums import DuelKind, EventType, Outcome, PossessionOrigin, SetPiece, ShotOutcome
from football_platform.canonical.models import SHOOTOUT_PERIOD

# PPDA zones (Trainor's public definition): the opponent's own 60 % of the pitch.
PPDA_OPPONENT_ZONE_MAX_X = 0.6 * PITCH_LENGTH_M  # opponent's frame: passes before x = 63 m
PPDA_DEFENSIVE_ZONE_MIN_X = 0.4 * PITCH_LENGTH_M  # defending team's frame: actions from x = 42 m
# Throw-ins are excluded: most throw-in possessions become ordinary open play (Phase 8 validation).
SET_PIECE_ORIGINS = {PossessionOrigin.CORNER.value, PossessionOrigin.FREE_KICK.value}

TEAM_EVENT_COLUMNS = (
    "id", "match_id", "period", "team_id", "type", "outcome", "start_x", "start_y", "end_x", "end_y",
    "set_piece", "duel_kind", "shot_outcome", "possession_origin", "pass_is_cross",
)


# -- Expected points -------------------------------------------------------------------

def goal_distribution(shot_xgs: np.ndarray) -> np.ndarray:
    """P(k goals), k = 0..n, when each shot scores independently with probability = its xG."""
    distribution = np.array([1.0])
    for p in shot_xgs:
        distribution = np.convolve(distribution, [1.0 - p, p])
    return distribution


def expected_points(team_xgs: np.ndarray, opponent_xgs: np.ndarray) -> float:
    team = goal_distribution(team_xgs)
    opponent = goal_distribution(opponent_xgs)
    joint = np.outer(team, opponent)  # joint[i, j] = P(team scores i, opponent scores j)
    p_win = np.tril(joint, k=-1).sum()
    p_draw = np.trace(joint)
    return float(3 * p_win + p_draw)


# -- Team-match statistics ---------------------------------------------------------------

def _opponents(matches: pd.DataFrame) -> pd.DataFrame:
    """One row per (match, team) with its opponent, goals and points (official scores)."""
    home = matches.assign(team_id=matches["home_team_id"], opponent_id=matches["away_team_id"],
                          goals_for=matches["home_score"], goals_against=matches["away_score"])
    away = matches.assign(team_id=matches["away_team_id"], opponent_id=matches["home_team_id"],
                          goals_for=matches["away_score"], goals_against=matches["home_score"])
    sides = pd.concat([home, away], ignore_index=True).rename(columns={"id": "match_id"})
    sides["points"] = np.select(
        [sides["goals_for"] > sides["goals_against"], sides["goals_for"] == sides["goals_against"]], [3, 1], 0
    )
    return sides[["match_id", "season_id", "team_id", "opponent_id", "goals_for", "goals_against", "points"]]


def team_match_stats(events: pd.DataFrame, provider_metrics: pd.DataFrame, matches: pd.DataFrame) -> pd.DataFrame:
    """One row per (match, team): result, xG, xPts and style components (season ratios come later)."""
    missing = set(TEAM_EVENT_COLUMNS) - set(events.columns)
    if missing:
        raise ValueError(f"events is missing columns: {sorted(missing)}")
    ev = events[events["period"] != SHOOTOUT_PERIOD].copy()
    for column in ("start_x", "start_y", "end_x", "end_y"):
        ev[column] = ev[column].astype("float64")
    xg = shot_xg(provider_metrics)

    is_shot = ev["type"] == EventType.SHOT.value
    is_penalty = ev["set_piece"] == SetPiece.PENALTY.value
    np_shot = is_shot & ~is_penalty
    shot_xg_values = ev["id"].map(xg)
    is_pass = ev["type"] == EventType.PASS.value
    attempted = is_pass & ev["outcome"].isin([Outcome.SUCCESS.value, Outcome.FAIL.value])
    open_play_completed = is_pass & (ev["outcome"] == Outcome.SUCCESS.value) & ev["set_piece"].isna()
    length = np.hypot(ev["end_x"] - ev["start_x"], ev["end_y"] - ev["start_y"])
    defensive_action = (
        ((ev["type"] == EventType.DUEL.value) & (ev["duel_kind"] == DuelKind.GROUND.value))
        | (ev["type"] == EventType.INTERCEPTION.value)
        | (ev["type"] == EventType.FOUL_COMMITTED.value)
    )
    np_xg = shot_xg_values.where(np_shot, 0.0).fillna(0.0)
    origin = ev["possession_origin"]

    per_event = pd.DataFrame({
        "match_id": ev["match_id"],
        "team_id": ev["team_id"],
        "np_shots": np_shot,
        "npxg": np_xg,
        "passes_attempted": attempted,
        "long_passes": attempted & (length >= LONG_PASS_M),
        "open_play_completed_passes": open_play_completed,
        "progressive_passes": open_play_completed & is_progressive(ev["start_x"], ev["start_y"], ev["end_x"], ev["end_y"]),
        "crosses": attempted & ev["pass_is_cross"].fillna(False).astype(bool) & ev["set_piece"].isna(),
        "counter_npxg": np_xg.where(origin == PossessionOrigin.COUNTER.value, 0.0),
        "set_piece_npxg": np_xg.where(origin.isin(SET_PIECE_ORIGINS), 0.0),
        # PPDA components, each in the acting team's frame:
        "passes_in_own_60": is_pass & (ev["start_x"] < PPDA_OPPONENT_ZONE_MAX_X),
        "defensive_actions_high": defensive_action & (ev["start_x"] >= PPDA_DEFENSIVE_ZONE_MIN_X),
    })
    own = per_event.groupby(["match_id", "team_id"]).sum().reset_index()

    stats = _opponents(matches).merge(own, on=["match_id", "team_id"], how="left").fillna(0.0)
    opponent = own.rename(columns={"team_id": "opponent_id"})[
        ["match_id", "opponent_id", "np_shots", "npxg", "passes_in_own_60"]
    ].rename(columns={"np_shots": "np_shots_against", "npxg": "npxg_against",
                      "passes_in_own_60": "opponent_passes_in_own_60"})
    stats = stats.merge(opponent, on=["match_id", "opponent_id"], how="left").fillna(0.0)

    # Expected points from every shot's xG (penalties included), per match.
    shots = ev.loc[is_shot, ["match_id", "team_id"]].assign(xg=shot_xg_values[is_shot])
    shots_by_team = {key: group["xg"].dropna().to_numpy() for key, group in shots.groupby(["match_id", "team_id"])}
    empty = np.array([])
    stats["xpts"] = [
        expected_points(shots_by_team.get((m, t), empty), shots_by_team.get((m, o), empty))
        for m, t, o in zip(stats["match_id"], stats["team_id"], stats["opponent_id"])
    ]
    return stats


# -- Team-season statistics --------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class TeamMetric:
    key: str
    label: str
    capability: str | None = None


TEAM_METRICS: tuple[TeamMetric, ...] = (
    TeamMetric("points_per_match", "Points per match"),
    TeamMetric("xpts_per_match", "Expected points per match", "has_provider_xg"),
    TeamMetric("goal_diff_per_match", "Goal difference per match"),
    TeamMetric("npxg_diff_per_match", "npxG difference per match", "has_provider_xg"),
    TeamMetric("npxg_for_per_match", "npxG for per match", "has_provider_xg"),
    TeamMetric("npxg_against_per_match", "npxG against per match", "has_provider_xg"),
    TeamMetric("npxg_per_shot_for", "npxG per shot (for)", "has_provider_xg"),
    TeamMetric("npxg_per_shot_against", "npxG per shot (against)", "has_provider_xg"),
    TeamMetric("possession_pct", "Possession %"),
    TeamMetric("ppda", "PPDA (passes allowed per defensive action)"),
    TeamMetric("long_pass_share", "Long pass share"),
    TeamMetric("progressive_pass_share", "Progressive pass share"),
    TeamMetric("crosses_per_match", "Open-play crosses per match"),
    TeamMetric("counter_npxg_share", "Share of npxG from counter-attacks", "has_possession_ids"),
    TeamMetric("set_piece_npxg_share", "Share of npxG from set pieces", "has_possession_ids"),
)


def team_season_stats(team_match: pd.DataFrame, capabilities: ProviderCapabilities,
                      team_possession: pd.DataFrame) -> pd.DataFrame:
    """Ratios of season totals per (team, season). team_possession: match_id, team_id, possession_pct."""
    tm = team_match.merge(team_possession, on=["match_id", "team_id"], how="left")
    sums = tm.groupby(["team_id", "season_id"]).agg(
        matches=("match_id", "nunique"),
        points=("points", "sum"), xpts=("xpts", "sum"),
        goals_for=("goals_for", "sum"), goals_against=("goals_against", "sum"),
        npxg_for=("npxg", "sum"), npxg_against=("npxg_against", "sum"),
        np_shots_for=("np_shots", "sum"), np_shots_against=("np_shots_against", "sum"),
        passes_attempted=("passes_attempted", "sum"), long_passes=("long_passes", "sum"),
        open_play_completed_passes=("open_play_completed_passes", "sum"),
        progressive_passes=("progressive_passes", "sum"), crosses=("crosses", "sum"),
        counter_npxg=("counter_npxg", "sum"), set_piece_npxg=("set_piece_npxg", "sum"),
        opponent_passes_in_own_60=("opponent_passes_in_own_60", "sum"),
        defensive_actions_high=("defensive_actions_high", "sum"),
        possession_pct=("possession_pct", "mean"),
    ).reset_index()
    n = sums["matches"]
    safe = lambda s: s.replace(0, np.nan)  # noqa: E731
    season = sums.assign(
        points_per_match=sums["points"] / n,
        xpts_per_match=sums["xpts"] / n,
        goal_diff_per_match=(sums["goals_for"] - sums["goals_against"]) / n,
        npxg_diff_per_match=(sums["npxg_for"] - sums["npxg_against"]) / n,
        npxg_for_per_match=sums["npxg_for"] / n,
        npxg_against_per_match=sums["npxg_against"] / n,
        npxg_per_shot_for=sums["npxg_for"] / safe(sums["np_shots_for"]),
        npxg_per_shot_against=sums["npxg_against"] / safe(sums["np_shots_against"]),
        ppda=sums["opponent_passes_in_own_60"] / safe(sums["defensive_actions_high"]),
        long_pass_share=sums["long_passes"] / safe(sums["passes_attempted"]),
        progressive_pass_share=sums["progressive_passes"] / safe(sums["open_play_completed_passes"]),
        crosses_per_match=sums["crosses"] / n,
        counter_npxg_share=sums["counter_npxg"] / safe(sums["npxg_for"]),
        set_piece_npxg_share=sums["set_piece_npxg"] / safe(sums["npxg_for"]),
    )
    for metric in TEAM_METRICS:
        if metric.capability and not getattr(capabilities, metric.capability):
            season[metric.key] = np.nan
    return season


def add_team_percentiles(team_seasons: pd.DataFrame, population_season_ids: list[str]) -> pd.DataFrame:
    """Percentile of each metric **within its league-season** (complete seasons only).

    Within-league, not pooled: league norms differ (e.g. mean PPDA 13.0 in La Liga vs 15.5 in
    the Premier League in 2015/16), and a league is the population a team actually competes in.
    """
    result = team_seasons.copy()
    population = result[result["season_id"].isin(population_season_ids)]
    by_league = population.groupby("season_id")
    for metric in TEAM_METRICS:
        result[f"{metric.key}_pct"] = by_league[metric.key].rank(method="average", pct=True) * 100
    result["league_size"] = by_league["team_id"].transform("size")
    return result
