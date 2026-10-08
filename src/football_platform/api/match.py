"""Match report assembly (Phase 11.4-11.5, D028). Aggregates only: binned xG, team totals, networks."""

from __future__ import annotations

from typing import Any

import pandas as pd

from football_platform.analytics.match_report import passing_network, period_lengths, xg_race
from football_platform.analytics.player_match import player_match_stats, shot_xg
from football_platform.analytics.possession import team_match_possession
from football_platform.analytics.team import expected_points, team_match_stats
from football_platform.analytics.xt import XTModel, action_values
from football_platform.api.profile import DATA_SOURCE
from football_platform.canonical.enums import EventType
from football_platform.canonical.models import SHOOTOUT_PERIOD

STANDOUTS_PER_CATEGORY = 3
COORDINATES = ["start_x", "start_y", "end_x", "end_y", "time_s"]
NETWORK_NOTE = (
    "Starting XI until the team's first substitution or dismissal. Positions are averages of where each player "
    "passed and received, mixing attacking and defending phases: read them as tendencies, not a formation."
)


def _frames(events: list[dict], metrics: list[dict], apps: list[dict], spells: list[dict]):
    ev = pd.DataFrame(events)
    for column in COORDINATES:
        ev[column] = ev[column].astype(float)
    ev = ev.astype({c: str for c in ("id", "team_id", "match_id")})  # UUIDs from the DB -> str, as in matches_df
    for column in ("player_id", "pass_recipient_id", "pass_assisted_shot_event_id"):
        ev[column] = ev[column].map(lambda v: None if v is None else str(v))
    m = pd.DataFrame(metrics, columns=["event_id", "metric_key", "value", "source_provider", "model_version"])
    m["event_id"] = m["event_id"].astype(str)
    a = pd.DataFrame(apps)
    a[["team_id", "player_id", "match_id"]] = a[["team_id", "player_id", "match_id"]].astype(str)
    s = pd.DataFrame(spells, columns=["match_id", "team_id", "player_id", "period", "start_s", "end_s", "role"])
    s[["team_id", "player_id", "match_id"]] = s[["team_id", "player_id", "match_id"]].astype(str)
    return ev, m, a, s


def build_match_report(match: dict[str, Any], events: list[dict], metrics: list[dict], apps: list[dict],
                       spells: list[dict], xt: XTModel | None) -> dict[str, Any]:
    ev, m, a, s = _frames(events, metrics, apps, spells)
    home, away = str(match["home_team_id"]), str(match["away_team_id"])
    matches_df = pd.DataFrame([{**match, "id": str(match["id"]), "home_team_id": home, "away_team_id": away,
                                "season_id": str(match["season_id"])}])
    lengths = period_lengths(ev)
    xg = shot_xg(m)
    in_play = ev[ev["period"] != SHOOTOUT_PERIOD]

    shots = in_play[in_play["type"] == EventType.SHOT.value].assign(xg=lambda d: d["id"].map(xg))
    own_goals = in_play[in_play["type"] == EventType.OWN_GOAL.value]
    race = xg_race(shots, own_goals, lengths, home, away)

    xpts = {home: expected_points(shots.loc[shots["team_id"] == home, "xg"].dropna().to_numpy(),
                                  shots.loc[shots["team_id"] == away, "xg"].dropna().to_numpy())}
    xpts[away] = expected_points(shots.loc[shots["team_id"] == away, "xg"].dropna().to_numpy(),
                                 shots.loc[shots["team_id"] == home, "xg"].dropna().to_numpy())

    team = team_match_stats(ev, m, matches_df).set_index("team_id")
    possession = team_match_possession(ev).set_index("team_id")["possession_pct"]
    xt_values = action_values(ev, xt) if xt is not None else None
    names = dict(zip(a["player_id"], a["player_name"]))

    def team_view(team_id: str) -> dict[str, Any]:
        row = team.loc[team_id]
        actions = row["defensive_actions_high"]
        return {
            "team_id": team_id,
            "goals": int(row["goals_for"]),
            "xg": float(shots.loc[shots["team_id"] == team_id, "xg"].sum()),
            "npxg": float(row["npxg"]),
            "np_shots": int(row["np_shots"]),
            "xpts": xpts[team_id],
            "possession_pct": float(possession.get(team_id, float("nan"))),
            "passes": int(row["passes_attempted"]),
            "progressive_passes": int(row["progressive_passes"]),
            "crosses": int(row["crosses"]),
            "ppda": float(row["opponent_passes_in_own_60"] / actions) if actions else None,
            "high_ball_wins": int(row["high_ball_wins"]),
            "xt": float(xt_values[ev["team_id"] == team_id].sum()) if xt_values is not None else None,
            "network": _network(ev[ev["team_id"] == team_id], lengths, names),
            "lineup": _lineup(a[a["team_id"] == team_id]),
        }

    players = player_match_stats(ev, m, s, matches_df, xt)
    return {
        "match": {k: (str(v) if k.endswith("_id") or k == "id" else v) for k, v in match.items()},
        "home": team_view(home),
        "away": team_view(away),
        "xg_race": race,
        "standouts": _standouts(players, names, {home: match["home_team"], away: match["away_team"]}),
        "notes": {
            "xg_race": "Cumulative xG (penalties included) at the end of each 5-minute bin; dots mark goals.",
            "network": NETWORK_NOTE,
            "xpts": "Probability-weighted points from every shot's xG (each shot an independent chance).",
        },
        "data_source": DATA_SOURCE,
    }


def _network(team_events: pd.DataFrame, lengths: dict[int, float], names: dict[str, str]) -> dict[str, Any]:
    network = passing_network(team_events, lengths)
    for node in network["nodes"]:
        node["name"] = names.get(node["player_id"], "?")
    return network


def _lineup(team_apps: pd.DataFrame) -> list[dict[str, Any]]:
    ordered = team_apps.sort_values(["is_starter", "minutes_played"], ascending=[False, False])
    return [{"player_id": r.player_id, "name": r.player_name, "starter": bool(r.is_starter),
             "minutes": float(r.minutes_played), "shirt": r.shirt_number}
            for r in ordered.itertuples() if r.minutes_played > 0]


def _standouts(players: pd.DataFrame, names: dict[str, str], teams: dict[str, str]) -> list[dict[str, Any]]:
    """Leaders per category (descriptive, no composite rating)."""
    players = players.assign(
        xt=players["xt_pass"].fillna(0) + players["xt_carry"].fillna(0),
        ball_wins=players["tackles_won"] + players["interceptions"] + players["ball_recoveries"],
    )
    categories = [("npxg", "Non-penalty xG"), ("xt", "xT from passes and carries"),
                  ("key_passes", "Key passes"), ("ball_wins", "Ball wins")]
    result = []
    for key, label in categories:
        top = players[players[key] > 0].nlargest(STANDOUTS_PER_CATEGORY, key)
        result.append({"key": key, "label": label, "players": [
            {"player_id": r.player_id, "name": names.get(r.player_id, "?"), "team": teams.get(r.team_id, ""),
             "value": float(getattr(r, key))} for r in top.itertuples()]})
    return result
