"""Player-match counting statistics from canonical events.

Definitions: docs/FOOTBALL_ANALYTICS.md, "Phase 4" and "Phase 4.1".
Input columns use canonical names (the `events` and `provider_metrics` tables).

For every count metric `m`, the output also holds `m__sq`, the sum of squared
per-event contributions. It is the noise term of the regressed estimates
(Phase 4.1 §4): equal to the count for event counts, Σ xG² for xG metrics.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from football_platform.analytics.definitions import FINAL_THIRD_X, LONG_PASS_M
from football_platform.analytics.geometry import in_penalty_area, is_progressive
from football_platform.analytics.goalkeeping import GK_COLUMNS, goalkeeper_match_stats
from football_platform.canonical.enums import (
    DuelKind,
    EventType,
    GoalkeeperActionKind,
    Outcome,
    SetPiece,
    ShotOutcome,
)
from football_platform.canonical.models import SHOOTOUT_PERIOD

EVENT_COLUMNS = (
    "id", "match_id", "period", "time_s", "team_id", "player_id", "type", "outcome",
    "start_x", "start_y", "end_x", "end_y", "set_piece", "duel_kind", "aerial_won",
    "shot_outcome", "pass_is_shot_assist", "pass_is_goal_assist", "pass_assisted_shot_event_id",
    "goalkeeper_action_kind",
)
KEYS = ["match_id", "player_id", "team_id"]
COORDINATE_COLUMNS = ["start_x", "start_y", "end_x", "end_y"]
XG_METRIC_KEY = "xg"


class MixedProviderMetricError(ValueError):
    """Raised when one provider's xG would be mixed with another's (decision D007)."""


def shot_xg(provider_metrics: pd.DataFrame) -> pd.Series:
    """Provider xG per shot event id. Refuses to mix providers or model versions."""
    xg = provider_metrics[provider_metrics["metric_key"] == XG_METRIC_KEY]
    sources = xg[["source_provider", "model_version"]].drop_duplicates()
    if len(sources) > 1:
        raise MixedProviderMetricError(f"xG from several sources: {sources.to_dict('records')}")
    return xg.set_index("event_id")["value"]


def _flag(series: pd.Series) -> pd.Series:
    """Nullable boolean column -> plain bool (absent flag = False)."""
    return series.fillna(False).astype(bool)


def _event_indicators(ev: pd.DataFrame, xg: pd.Series) -> pd.DataFrame:
    """One row per event, one column per metric: the event's contribution (0/1 or xG)."""
    event_type = ev["type"]
    outcome = ev["outcome"]
    completed = outcome == Outcome.SUCCESS.value
    open_play = ev["set_piece"].isna()

    is_shot = event_type == EventType.SHOT.value
    is_penalty = ev["set_piece"] == SetPiece.PENALTY.value
    np_shot = is_shot & ~is_penalty
    goal = ev["shot_outcome"] == ShotOutcome.GOAL.value

    is_pass = event_type == EventType.PASS.value
    attempted = is_pass & outcome.isin([Outcome.SUCCESS.value, Outcome.FAIL.value])
    shot_assist = _flag(ev["pass_is_shot_assist"])
    goal_assist = _flag(ev["pass_is_goal_assist"])
    progressive = is_progressive(ev["start_x"], ev["start_y"], ev["end_x"], ev["end_y"])
    length = np.hypot(ev["end_x"] - ev["start_x"], ev["end_y"] - ev["start_y"])
    end_in_box = in_penalty_area(ev["end_x"], ev["end_y"])
    start_in_box = in_penalty_area(ev["start_x"], ev["start_y"])

    is_duel = event_type == EventType.DUEL.value
    ground_duel = is_duel & (ev["duel_kind"] == DuelKind.GROUND.value)
    aerial_lost = is_duel & (ev["duel_kind"] == DuelKind.AERIAL.value) & (outcome == Outcome.FAIL.value)
    gk_kind = ev["goalkeeper_action_kind"]

    shot_xg_values = ev["id"].map(xg).where(np_shot)
    if xg.size and (np_shot & shot_xg_values.isna()).any():
        raise ValueError(f"{int((np_shot & shot_xg_values.isna()).sum())} non-penalty shots have no xG value")

    return pd.DataFrame(
        {
            "np_shots": np_shot,
            "np_goals": np_shot & goal,
            "penalty_goals": is_shot & is_penalty & goal,
            "npxg": shot_xg_values.fillna(0.0),
            "assists": is_pass & goal_assist,
            "key_passes": is_pass & (shot_assist | goal_assist),
            # xA: xG of the shot each pass assisted, credited to the passer.
            "xa": ev["pass_assisted_shot_event_id"].map(xg).where(is_pass).fillna(0.0),
            "passes_attempted": attempted,
            "passes_completed": is_pass & completed,
            "long_passes_attempted": attempted & (length >= LONG_PASS_M),
            "progressive_passes": is_pass & completed & open_play & progressive,
            "progressive_carries": (event_type == EventType.CARRY.value) & progressive,
            "passes_into_final_third": is_pass & completed & open_play
            & (ev["start_x"] < FINAL_THIRD_X) & (ev["end_x"] >= FINAL_THIRD_X),
            "passes_into_box": is_pass & completed & open_play & end_in_box & ~start_in_box,
            "tackles": ground_duel,
            "tackles_won": ground_duel & completed,
            "interceptions": event_type == EventType.INTERCEPTION.value,
            "ball_recoveries": (event_type == EventType.BALL_RECOVERY.value) & completed,
            "pressures": event_type == EventType.PRESSURE.value,
            "aerials_won": _flag(ev["aerial_won"]),
            "aerials_lost": aerial_lost,
            "gk_claims": gk_kind.isin([GoalkeeperActionKind.CLAIM.value, GoalkeeperActionKind.PUNCH.value]),
            "gk_sweeper_actions": gk_kind == GoalkeeperActionKind.SWEEPER.value,
        },
        index=ev.index,
    ).astype("float64")


def player_match_stats(
    events: pd.DataFrame,
    provider_metrics: pd.DataFrame,
    position_spells: pd.DataFrame,
    matches: pd.DataFrame,
) -> pd.DataFrame:
    """One row per (match, player, team) with every count metric, its `__sq` term,
    goalkeeper shot-stopping counts and `aerials_total`.

    position_spells needs match_id, team_id, player_id, period, start_s, end_s, role;
    matches needs id, home_team_id, away_team_id.
    """
    missing = set(EVENT_COLUMNS) - set(events.columns)
    if missing:
        raise ValueError(f"events is missing columns: {sorted(missing)}")

    events = events.copy()
    events[COORDINATE_COLUMNS] = events[COORDINATE_COLUMNS].astype("float64")  # missing -> NaN
    in_play = events[events["period"] != SHOOTOUT_PERIOD]
    ev = in_play[in_play["player_id"].notna()]

    contributions = _event_indicators(ev, shot_xg(provider_metrics))
    squared = (contributions**2).add_suffix("__sq")
    per_event = pd.concat([ev[KEYS], contributions, squared], axis=1)
    stats = per_event.groupby(KEYS, sort=False).sum().reset_index()

    # Goalkeeper shot-stopping (Phase 4.1 §3): counts of opponent shots.
    gk = goalkeeper_match_stats(in_play, position_spells, matches)
    gk = gk.assign(**{f"{c}__sq": gk[c] for c in GK_COLUMNS})
    stats = stats.merge(gk, on=KEYS, how="outer")
    value_columns = [c for c in stats.columns if c not in KEYS]
    stats[value_columns] = stats[value_columns].fillna(0.0)

    stats["aerials_total"] = stats["aerials_won"] + stats["aerials_lost"]
    return stats
