"""Store a player-season report as the current analytics snapshot (decision D018)."""

from __future__ import annotations

import math
import uuid
from typing import Any

import pandas as pd
import psycopg

from football_platform.analytics.definitions import ALL_METRICS, MetricKind, MetricSpec

PLAYER_SEASON_COLUMNS = [
    "player_id", "season_id", "analytics_run_id", "team_ids", "minutes", "appearances", "starts",
    "primary_role", "primary_role_share", "position_group", "team_possession_pct", "eligible",
    "population_size",
]
INTEGER_COLUMNS = {"appearances", "starts", "population_size"}
METRIC_COLUMNS = [
    "player_id", "season_id", "metric_key", "total", "value", "percentile", "regressed", "reliability", "regressed_sd",
]


def _clean(value: Any) -> Any:
    """NaN/NA -> None so PostgreSQL stores NULL ("unavailable", never 0)."""
    if value is None or value is pd.NA:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def metric_row(row: pd.Series, metric: MetricSpec) -> tuple:
    if metric.kind is MetricKind.COUNT:
        total, value = row[metric.key], row[f"{metric.key}_p90"]
        percentile = row[f"{metric.key}_p90_pct"]
        regressed = row.get(f"{metric.key}_p90_regressed")
        reliability = row.get(f"{metric.key}_reliability")
        regressed_sd = row.get(f"{metric.key}_p90_regressed_sd")
    else:
        total, value = row[metric.numerator], row[metric.key]
        percentile, regressed, reliability, regressed_sd = row[f"{metric.key}_pct"], None, None, None
    return tuple(_clean(v) for v in (row["player_id"], row["season_id"], metric.key, total, value,
                                     percentile, regressed, reliability, regressed_sd))


def store_snapshot(conn: psycopg.Connection, report: pd.DataFrame, min_minutes: float,
                   population_seasons: list[str], source_provider: str) -> str:
    """Replace the current snapshot with `report` in one transaction. Returns the run id."""
    run_id = str(uuid.uuid4())
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(
            """INSERT INTO analytics_runs (id, min_minutes, population_seasons, source_provider, row_count)
               VALUES (%s, %s, %s::uuid[], %s, %s)""",
            (run_id, min_minutes, population_seasons, source_provider, len(report)),
        )
        cur.execute("DELETE FROM player_seasons")  # cascades to player_season_metrics
        with cur.copy(f"COPY player_seasons ({', '.join(PLAYER_SEASON_COLUMNS)}) FROM STDIN") as copy:
            for _, row in report.iterrows():
                values = {**row.to_dict(), "analytics_run_id": run_id, "team_ids": list(row["team_ids"])}
                cleaned = {c: _clean(values[c]) for c in PLAYER_SEASON_COLUMNS}
                for column in INTEGER_COLUMNS:
                    if cleaned[column] is not None:
                        cleaned[column] = int(cleaned[column])
                copy.write_row(tuple(cleaned[c] for c in PLAYER_SEASON_COLUMNS))
        with cur.copy(f"COPY player_season_metrics ({', '.join(METRIC_COLUMNS)}) FROM STDIN") as copy:
            for _, row in report.iterrows():
                for metric in ALL_METRICS:
                    copy.write_row(metric_row(row, metric))
    return run_id


def store_team_snapshot(conn: psycopg.Connection, report: pd.DataFrame) -> int:
    """Replace the team-season snapshot (Phase 8). Returns the number of team-seasons stored."""
    from football_platform.analytics.team import TEAM_METRICS

    with conn.transaction(), conn.cursor() as cur:
        cur.execute("DELETE FROM team_seasons")  # cascades to team_season_metrics
        columns = ["team_id", "season_id", "matches", "points", "goals_for", "goals_against", "league_size"]
        with cur.copy(f"COPY team_seasons ({', '.join(columns)}) FROM STDIN") as copy:
            for _, row in report.iterrows():
                values = [_clean(row[c]) for c in columns]
                copy.write_row([values[0], values[1]] + [None if v is None else int(v) for v in values[2:]])
        with cur.copy("COPY team_season_metrics (team_id, season_id, metric_key, value, percentile) FROM STDIN") as copy:
            for _, row in report.iterrows():
                for metric in TEAM_METRICS:
                    copy.write_row((row["team_id"], row["season_id"], metric.key,
                                    _clean(row[metric.key]), _clean(row[f"{metric.key}_pct"])))
    return len(report)
