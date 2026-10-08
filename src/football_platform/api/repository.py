"""Read-only queries on the canonical tables and the analytics snapshot."""

from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import dict_row

SEARCH_LIMIT_MAX = 100


def _rows(conn: psycopg.Connection, query: str, params: Any = None) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)
        return cur.fetchall()


def latest_run(conn: psycopg.Connection) -> dict[str, Any] | None:
    rows = _rows(conn, "SELECT id, created_at, min_minutes, population_seasons, source_provider, row_count "
                       "FROM analytics_runs ORDER BY created_at DESC LIMIT 1")
    return rows[0] if rows else None


def seasons(conn: psycopg.Connection) -> list[dict[str, Any]]:
    return _rows(conn, """
        SELECT s.id, s.label, s.coverage_scope, c.name AS competition, c.gender,
               (SELECT count(*) FROM player_seasons ps WHERE ps.season_id = s.id) AS player_count
        FROM seasons s JOIN competitions c ON c.id = s.competition_id
        ORDER BY c.name, s.label""")


TEAM_NAMES = """(SELECT array_agg(t.name ORDER BY t.name) FROM teams t WHERE t.id = ANY(ps.team_ids))"""


def search_players(conn: psycopg.Connection, query: str | None, season_id: str | None,
                   position_group: str | None, eligible_only: bool, limit: int) -> list[dict[str, Any]]:
    conditions, params = [], []
    if query:
        # Accent-insensitive (migration 0003). 2.5k players: no index needed.
        conditions.append("(unaccent(p.name) ILIKE unaccent(%s) OR unaccent(p.known_name) ILIKE unaccent(%s))")
    if season_id:
        conditions.append("ps.season_id = %s")
    if position_group:
        conditions.append("ps.position_group = %s")
    if eligible_only:
        conditions.append("ps.eligible")
    where = " AND ".join(conditions) or "TRUE"
    sql = f"""
        SELECT ps.player_id, ps.season_id, coalesce(p.known_name, p.name) AS player_name,
               {TEAM_NAMES} AS teams, c.name AS competition, s.label AS season_label,
               ps.position_group, ps.primary_role, ps.minutes, ps.eligible
        FROM player_seasons ps
        JOIN players p ON p.id = ps.player_id
        JOIN seasons s ON s.id = ps.season_id
        JOIN competitions c ON c.id = s.competition_id
        WHERE {where}
        ORDER BY ps.minutes DESC
        LIMIT %s"""
    if query:
        like = f"%{query}%"
        params += [like, like]
    params += [p for p in (season_id, position_group) if p]
    params.append(min(limit, SEARCH_LIMIT_MAX))
    return _rows(conn, sql, params)


def player_season(conn: psycopg.Connection, player_id: str, season_id: str) -> dict[str, Any] | None:
    rows = _rows(conn, f"""
        SELECT ps.*, coalesce(p.known_name, p.name) AS player_name, p.nationality,
               {TEAM_NAMES} AS teams, c.name AS competition, s.label AS season_label,
               r.population_seasons, r.min_minutes,
               -- Size of the reference population, also for players outside it (not ranked).
               (SELECT count(*) FROM player_seasons pop
                WHERE pop.position_group = ps.position_group AND pop.eligible
                  AND pop.season_id = ANY(r.population_seasons)) AS population_group_size
        FROM player_seasons ps
        JOIN players p ON p.id = ps.player_id
        JOIN seasons s ON s.id = ps.season_id
        JOIN competitions c ON c.id = s.competition_id
        JOIN analytics_runs r ON r.id = ps.analytics_run_id
        WHERE ps.player_id = %s AND ps.season_id = %s""", (player_id, season_id))
    return rows[0] if rows else None


def player_season_metrics(conn: psycopg.Connection, player_id: str, season_id: str) -> dict[str, dict[str, Any]]:
    rows = _rows(conn, """
        SELECT metric_key, total, value, percentile, regressed, reliability, regressed_sd
        FROM player_season_metrics WHERE player_id = %s AND season_id = %s""", (player_id, season_id))
    return {row.pop("metric_key"): row for row in rows}


def scouting_population(conn: psycopg.Connection, position_group: str, metric_keys: list[str],
                        season_id: str | None, min_possession: float | None,
                        max_possession: float | None) -> list[dict[str, Any]]:
    """Eligible players of a group in the latest snapshot's population, one row per (player, metric)."""
    conditions = ["ps.position_group = %s", "ps.eligible", "ps.season_id = ANY(r.population_seasons)"]
    params: list[Any] = [metric_keys, position_group]
    if season_id:
        conditions.append("ps.season_id = %s")
        params.append(season_id)
    if min_possession is not None:
        conditions.append("ps.team_possession_pct >= %s")
        params.append(min_possession)
    if max_possession is not None:
        conditions.append("ps.team_possession_pct <= %s")
        params.append(max_possession)
    return _rows(conn, f"""
        SELECT ps.player_id, ps.season_id, coalesce(p.known_name, p.name) AS player_name,
               {TEAM_NAMES} AS teams, c.name AS competition, s.label AS season_label,
               ps.minutes, ps.team_possession_pct, ps.primary_role,
               m.metric_key, m.percentile, m.value, m.reliability
        FROM player_seasons ps
        JOIN analytics_runs r ON r.id = ps.analytics_run_id
        JOIN players p ON p.id = ps.player_id
        JOIN seasons s ON s.id = ps.season_id
        JOIN competitions c ON c.id = s.competition_id
        LEFT JOIN player_season_metrics m
               ON m.player_id = ps.player_id AND m.season_id = ps.season_id AND m.metric_key = ANY(%s)
        WHERE {' AND '.join(conditions)}""", params)


TEAM_SEASON_SELECT = """
    SELECT ts.team_id, ts.season_id, t.name AS team_name, c.name AS competition, s.label AS season_label,
           ts.matches, ts.points, ts.goals_for, ts.goals_against, ts.league_size
    FROM team_seasons ts
    JOIN teams t ON t.id = ts.team_id
    JOIN seasons s ON s.id = ts.season_id
    JOIN competitions c ON c.id = s.competition_id"""


def team_seasons(conn: psycopg.Connection, season_id: str | None) -> list[dict[str, Any]]:
    where, params = ("WHERE ts.season_id = %s", [season_id]) if season_id else ("", [])
    return _rows(conn, f"{TEAM_SEASON_SELECT} {where} ORDER BY c.name, ts.points DESC, t.name", params)


def team_season(conn: psycopg.Connection, team_id: str, season_id: str) -> dict[str, Any] | None:
    rows = _rows(conn, f"{TEAM_SEASON_SELECT} WHERE ts.team_id = %s AND ts.season_id = %s", (team_id, season_id))
    return rows[0] if rows else None


def team_season_metrics(conn: psycopg.Connection, season_id: str | None,
                        team_id: str | None = None) -> dict[tuple[str, str], dict[str, dict[str, Any]]]:
    """(team_id, season_id) -> metric_key -> {value, percentile}."""
    conditions, params = [], []
    if season_id:
        conditions.append("season_id = %s")
        params.append(season_id)
    if team_id:
        conditions.append("team_id = %s")
        params.append(team_id)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    result: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    for row in _rows(conn, f"SELECT team_id, season_id, metric_key, value, percentile FROM team_season_metrics {where}",
                     params):
        result.setdefault((str(row["team_id"]), str(row["season_id"])), {})[row["metric_key"]] = {
            "value": row["value"], "percentile": row["percentile"]}
    return result


def team_squad(conn: psycopg.Connection, team_id: str, season_id: str) -> list[dict[str, Any]]:
    """Players who appeared for the team (minutes over the whole season, possibly with another club too)."""
    return _rows(conn, """
        SELECT ps.player_id, ps.season_id, coalesce(p.known_name, p.name) AS player_name,
               ps.primary_role, ps.position_group, ps.minutes, ps.eligible,
               cardinality(ps.team_ids) > 1 AS multiple_clubs
        FROM player_seasons ps JOIN players p ON p.id = ps.player_id
        WHERE ps.season_id = %s AND %s = ANY(ps.team_ids)
        ORDER BY ps.minutes DESC""", (season_id, team_id))


def similarity_population(conn: psycopg.Connection, position_group: str, metric_keys: list[str],
                          target_player_id: str, target_season_id: str) -> list[dict[str, Any]]:
    """Eligible players of the group (snapshot population) plus the target, one row per (player, metric)."""
    return _rows(conn, f"""
        SELECT ps.player_id, ps.season_id, coalesce(p.known_name, p.name) AS player_name,
               {TEAM_NAMES} AS teams, c.name AS competition, ps.minutes, ps.eligible,
               ps.team_possession_pct, m.metric_key, m.regressed
        FROM player_seasons ps
        JOIN analytics_runs r ON r.id = ps.analytics_run_id
        JOIN players p ON p.id = ps.player_id
        JOIN seasons s ON s.id = ps.season_id
        JOIN competitions c ON c.id = s.competition_id
        JOIN player_season_metrics m
          ON m.player_id = ps.player_id AND m.season_id = ps.season_id AND m.metric_key = ANY(%s)
        WHERE ps.position_group = %s
          AND ((ps.eligible AND ps.season_id = ANY(r.population_seasons))
               OR (ps.player_id = %s AND ps.season_id = %s))""",
        (metric_keys, position_group, target_player_id, target_season_id))


SHOT_COLUMNS = """e.id, e.period, e.start_x, e.start_y, e.set_piece, e.shot_outcome, m.value AS xg"""
SHOT_JOIN = """FROM events e
        JOIN matches mt ON mt.id = e.match_id
        LEFT JOIN provider_metrics m ON m.event_id = e.id AND m.metric_key = 'xg'"""


def player_shots(conn: psycopg.Connection, player_id: str, season_id: str) -> list[dict[str, Any]]:
    return _rows(conn, f"""SELECT {SHOT_COLUMNS} {SHOT_JOIN}
        WHERE e.type = 'shot' AND e.player_id = %s AND mt.season_id = %s""", (player_id, season_id))


def group_shots(conn: psycopg.Connection, position_group: str) -> list[dict[str, Any]]:
    """Shots of eligible players of a group in the snapshot population (zone baseline)."""
    return _rows(conn, f"""SELECT {SHOT_COLUMNS} {SHOT_JOIN}
        JOIN player_seasons ps ON ps.player_id = e.player_id AND ps.season_id = mt.season_id
        JOIN analytics_runs r ON r.id = ps.analytics_run_id
        WHERE e.type = 'shot' AND ps.position_group = %s AND ps.eligible
          AND ps.season_id = ANY(r.population_seasons)""", (position_group,))


def team_shots(conn: psycopg.Connection, team_id: str, season_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(shots for, shots against) in the team's matches of the season."""
    base = f"""SELECT {SHOT_COLUMNS} {SHOT_JOIN}
        WHERE e.type = 'shot' AND mt.season_id = %s AND (mt.home_team_id = %s OR mt.away_team_id = %s)"""
    shots_for = _rows(conn, base + " AND e.team_id = %s", (season_id, team_id, team_id, team_id))
    shots_against = _rows(conn, base + " AND e.team_id <> %s", (season_id, team_id, team_id, team_id))
    return shots_for, shots_against


def league_shots(conn: psycopg.Connection, season_id: str) -> list[dict[str, Any]]:
    return _rows(conn, f"SELECT {SHOT_COLUMNS} {SHOT_JOIN} WHERE e.type = 'shot' AND mt.season_id = %s", (season_id,))


ZONE_EVENT_COLUMNS = "e.period, e.type, e.outcome, e.set_piece, e.start_x, e.start_y, e.end_x, e.end_y"
ZONE_TYPES = ["pass", "shot", "take_on", "ball_recovery", "interception", "clearance", "miscontrol", "dispossessed",
              "carry"]


def player_zone_events(conn: psycopg.Connection, player_id: str, season_id: str) -> list[dict[str, Any]]:
    return _rows(conn, f"""SELECT {ZONE_EVENT_COLUMNS} FROM events e JOIN matches mt ON mt.id = e.match_id
        WHERE e.player_id = %s AND mt.season_id = %s AND e.type = ANY(%s)""", (player_id, season_id, ZONE_TYPES))


def passes_received(conn: psycopg.Connection, player_id: str, season_id: str) -> list[dict[str, Any]]:
    return _rows(conn, f"""SELECT {ZONE_EVENT_COLUMNS} FROM events e JOIN matches mt ON mt.id = e.match_id
        WHERE e.pass_recipient_id = %s AND mt.season_id = %s AND e.type = 'pass'""", (player_id, season_id))


GROUP_SEASONS = """JOIN player_seasons ps ON ps.player_id = {player} AND ps.season_id = mt.season_id
        JOIN analytics_runs r ON r.id = ps.analytics_run_id
        WHERE ps.position_group = %s AND ps.eligible AND ps.season_id = ANY(r.population_seasons)"""


def group_zone_events(conn: psycopg.Connection, position_group: str) -> list[dict[str, Any]]:
    return _rows(conn, f"""SELECT {ZONE_EVENT_COLUMNS} FROM events e JOIN matches mt ON mt.id = e.match_id
        {GROUP_SEASONS.format(player="e.player_id")} AND e.type = ANY(%s)""", (position_group, ZONE_TYPES))


def group_passes_received(conn: psycopg.Connection, position_group: str) -> list[dict[str, Any]]:
    return _rows(conn, f"""SELECT {ZONE_EVENT_COLUMNS} FROM events e JOIN matches mt ON mt.id = e.match_id
        {GROUP_SEASONS.format(player="e.pass_recipient_id")} AND e.type = 'pass'""", (position_group,))


PRESSING_TYPES = ["duel", "interception", "foul_committed", "ball_recovery"]
PRESSING_COLUMNS = "e.type, e.outcome, e.duel_kind, e.period, e.start_x, e.start_y"


def team_pressing_events(conn: psycopg.Connection, team_id: str, season_id: str) -> list[dict[str, Any]]:
    return _rows(conn, f"""SELECT {PRESSING_COLUMNS} FROM events e JOIN matches mt ON mt.id = e.match_id
        WHERE e.team_id = %s AND mt.season_id = %s AND e.type = ANY(%s)""", (team_id, season_id, PRESSING_TYPES))


def league_pressing_events(conn: psycopg.Connection, season_id: str) -> list[dict[str, Any]]:
    return _rows(conn, f"""SELECT {PRESSING_COLUMNS} FROM events e JOIN matches mt ON mt.id = e.match_id
        WHERE mt.season_id = %s AND e.type = ANY(%s)""", (season_id, PRESSING_TYPES))


MATCH_SELECT = """
    SELECT m.id, m.season_id, m.match_date, m.matchweek, m.stage, m.venue, m.referee,
           m.home_team_id, ht.name AS home_team, m.away_team_id, at.name AS away_team,
           m.home_score, m.away_score, c.name AS competition, s.label AS season_label
    FROM matches m
    JOIN teams ht ON ht.id = m.home_team_id
    JOIN teams at ON at.id = m.away_team_id
    JOIN seasons s ON s.id = m.season_id
    JOIN competitions c ON c.id = s.competition_id"""


def matches_list(conn: psycopg.Connection, season_id: str | None, team_id: str | None) -> list[dict[str, Any]]:
    conditions, params = [], []
    if season_id:
        conditions.append("m.season_id = %s")
        params.append(season_id)
    if team_id:
        conditions.append("(m.home_team_id = %s OR m.away_team_id = %s)")
        params += [team_id, team_id]
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return _rows(conn, f"{MATCH_SELECT} {where} ORDER BY m.match_date, ht.name LIMIT 500", params)


def match_row(conn: psycopg.Connection, match_id: str) -> dict[str, Any] | None:
    rows = _rows(conn, f"{MATCH_SELECT} WHERE m.id = %s", (match_id,))
    return rows[0] if rows else None


MATCH_EVENT_COLUMNS = (
    "id, match_id, period, time_s, team_id, player_id, type, outcome, start_x, start_y, end_x, end_y, set_piece, "
    "duel_kind, aerial_won, shot_outcome, pass_is_shot_assist, pass_is_goal_assist, pass_assisted_shot_event_id, "
    "goalkeeper_action_kind, possession_origin, pass_is_cross, pass_recipient_id, card_type"
)


def match_events(conn: psycopg.Connection, match_id: str) -> list[dict[str, Any]]:
    return _rows(conn, f"SELECT {MATCH_EVENT_COLUMNS} FROM events WHERE match_id = %s", (match_id,))


def match_metrics(conn: psycopg.Connection, match_id: str) -> list[dict[str, Any]]:
    return _rows(conn, """SELECT event_id, metric_key, value, source_provider, model_version
        FROM provider_metrics WHERE match_id = %s""", (match_id,))


def match_appearances(conn: psycopg.Connection, match_id: str) -> list[dict[str, Any]]:
    return _rows(conn, """SELECT a.match_id, a.team_id, a.player_id, a.is_starter, a.minutes_played, a.shirt_number,
               coalesce(p.known_name, p.name) AS player_name
        FROM appearances a JOIN players p ON p.id = a.player_id WHERE a.match_id = %s""", (match_id,))


def match_spells(conn: psycopg.Connection, match_id: str) -> list[dict[str, Any]]:
    return _rows(conn, """SELECT match_id, team_id, player_id, period, start_s, end_s, role
        FROM position_spells WHERE match_id = %s""", (match_id,))


def latest_xt_values(conn: psycopg.Connection) -> dict[str, Any] | None:
    rows = _rows(conn, """SELECT grid_columns, grid_rows, cell_values, actions, iterations
        FROM xt_models ORDER BY created_at DESC LIMIT 1""")
    return rows[0] if rows else None
