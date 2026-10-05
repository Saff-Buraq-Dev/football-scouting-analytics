"""Builders for small, synthetic StatsBomb-shaped records.

Hand-written to mirror the StatsBomb schema (docs/data/STATSBOMB_DATA_DICTIONARY.md).
No real StatsBomb data is stored in the repository (decision D004).
"""

from __future__ import annotations

import itertools
import json
from typing import Any

_counter = itertools.count(1)

HOME_TEAM = {"id": 100, "name": "Home FC"}
AWAY_TEAM = {"id": 200, "name": "Away FC"}


def raw_event(
    type_name: str,
    *,
    team: dict[str, Any] = HOME_TEAM,
    player_id: int | None = 1,
    period: int = 1,
    timestamp: str = "00:10:00.000",
    location: list[float] | None = None,
    play_pattern: str = "Regular Play",
    **extra: Any,
) -> dict[str, Any]:
    n = next(_counter)
    event: dict[str, Any] = {
        "id": f"00000000-0000-0000-0000-{n:012d}",
        "index": n,
        "period": period,
        "timestamp": timestamp,
        "minute": 10,
        "second": 0,
        "type": {"id": 0, "name": type_name},
        "possession": 1,
        "possession_team": team,
        "play_pattern": {"id": 1, "name": play_pattern},
        "team": team,
    }
    if player_id is not None:
        event["player"] = {"id": player_id, "name": f"Player {player_id}"}
    if location is not None:
        event["location"] = location
    event.update(extra)
    return event


def half_end(period: int, timestamp: str) -> list[dict[str, Any]]:
    """StatsBomb records one Half End per team."""
    return [
        raw_event("Half End", team=team, player_id=None, period=period, timestamp=timestamp)
        for team in (HOME_TEAM, AWAY_TEAM)
    ]


def spell(
    position: str,
    start: str,
    start_period: int,
    end: str | None,
    end_period: int | None,
    start_reason: str = "Starting XI",
    end_reason: str = "Final Whistle",
) -> dict[str, Any]:
    return {
        "position_id": 0,
        "position": position,
        "from": start,
        "to": end,
        "from_period": start_period,
        "to_period": end_period,
        "start_reason": start_reason,
        "end_reason": end_reason,
    }


def lineup_player(player_id: int, positions: list[dict[str, Any]], jersey: int = 10) -> dict[str, Any]:
    return {
        "player_id": player_id,
        "player_name": f"Player {player_id}",
        "player_nickname": None,
        "jersey_number": jersey,
        "country": {"id": 1, "name": "Testland"},
        "cards": [],
        "positions": positions,
    }


def competition(cid: int, sid: int, name: str, season: str, international: bool = False) -> dict[str, Any]:
    return {
        "competition_id": cid,
        "season_id": sid,
        "country_name": "England",
        "competition_name": name,
        "competition_gender": "male",
        "competition_youth": False,
        "competition_international": international,
        "season_name": season,
        "match_available_360": None,
    }


def match(match_id: int, home_score: int = 1, away_score: int = 0) -> dict[str, Any]:
    return {
        "match_id": match_id,
        "match_date": "2015-08-08",
        "kick_off": "15:00:00.000",
        "home_team": {"home_team_id": HOME_TEAM["id"], "home_team_name": HOME_TEAM["name"],
                      "home_team_gender": "male", "country": {"name": "England"}},
        "away_team": {"away_team_id": AWAY_TEAM["id"], "away_team_name": AWAY_TEAM["name"],
                      "away_team_gender": "male", "country": {"name": "England"}},
        "home_score": home_score,
        "away_score": away_score,
        "match_week": 1,
        "competition_stage": {"name": "Regular Season"},
        "stadium": {"name": "Test Ground"},
        "referee": {"name": "A. Referee"},
    }


def _write(path: Any, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


def write_synthetic_raw_store(root: Any, commit: str) -> None:
    """A tiny raw store: Premier League 2015/16 (reviewed complete) with one 1-0 match.

    (2, 27) is reviewed as complete in coverage_review.json; (999, 1) is not reviewed;
    (11, 27) is listed but has no match file.
    """
    data = root / commit / "data"
    _write(data / "competitions.json", [
        competition(2, 27, "Premier League", "2015/2016"),
        competition(11, 27, "La Liga", "2015/2016"),
        competition(999, 1, "Test Cup", "2020"),
    ])
    _write(data / "matches/2/27.json", [match(5001)])
    events = [
        raw_event("Pass", team=HOME_TEAM, player_id=1, location=[60, 40],
                  **{"pass": {"end_location": [100, 30], "recipient": {"id": 1, "name": "Player 1"}}}),
        raw_event("Shot", team=HOME_TEAM, player_id=1, location=[108, 40],
                  **{"shot": {"outcome": {"name": "Goal"}, "statsbomb_xg": 0.3, "end_location": [120, 40, 1.0]}}),
        *half_end(1, "00:46:00.000"),
        *half_end(2, "00:48:00.000"),
    ]
    _write(data / "events/5001.json", events)
    _write(data / "lineups/5001.json", [
        {"team_id": HOME_TEAM["id"], "team_name": HOME_TEAM["name"],
         "lineup": [lineup_player(1, [spell("Center Forward", "00:00", 1, None, None)])]},
        {"team_id": AWAY_TEAM["id"], "team_name": AWAY_TEAM["name"],
         "lineup": [lineup_player(2, [])]},
    ])
