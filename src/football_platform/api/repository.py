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
        SELECT metric_key, total, value, percentile, regressed, reliability
        FROM player_season_metrics WHERE player_id = %s AND season_id = %s""", (player_id, season_id))
    return {row.pop("metric_key"): row for row in rows}
