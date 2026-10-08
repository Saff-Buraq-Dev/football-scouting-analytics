"""Store a player-season report as the current analytics snapshot (decision D018)."""

from __future__ import annotations

import math
import uuid

import numpy as np
from typing import Any

import pandas as pd
import psycopg

from football_platform.analytics.definitions import ALL_METRICS, MetricKind, MetricSpec
from football_platform.analytics.xt import XTModel

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


def store_xt_model(conn: psycopg.Connection, model: XTModel) -> str:
    """Store a fitted xT surface (Phase 11.1). Returns its id; the latest one is used by the API."""
    model_id = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO xt_models (id, grid_columns, grid_rows, cell_values, actions, iterations)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (model_id, model.grid.columns, model.grid.rows, [float(v) for v in model.values], model.actions,
         model.iterations),
    )
    return model_id


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


def store_archetypes(conn: psycopg.Connection, report: pd.DataFrame) -> int:
    """Fit archetypes per group on eligible players and assign every player of the group (Phase 11.7)."""
    from football_platform.analytics.archetypes import ARCHETYPE_K, PROTOTYPES, fit_archetypes
    from football_platform.analytics.definitions import PositionGroup
    from football_platform.analytics.similarity import similarity_features

    assigned = 0
    with conn.transaction(), conn.cursor() as cur:
        cur.execute("DELETE FROM player_archetypes")
        cur.execute("DELETE FROM archetypes")
        for group in ARCHETYPE_K:
            features = similarity_features(PositionGroup(group))
            columns = [f"{f}_p90_regressed" for f in features]
            members = report[(report["position_group"] == group)].dropna(subset=columns)
            population = members[members["eligible"]]
            model = fit_archetypes(group, features, population[columns].to_numpy(float))
            order, distances = model.assign(members[columns].to_numpy(float))
            pop_mask = members["eligible"].to_numpy()
            for index in range(len(model.centroids)):
                in_type = np.where(pop_mask & (order[:, 0] == index))[0]
                closest = in_type[np.argsort(distances[in_type, 0])][:PROTOTYPES]
                description = model.describe(index)
                cur.execute(
                    """INSERT INTO archetypes (position_group, archetype_index, size, more_features, less_features,
                       prototypes, prototype_seasons) VALUES (%s, %s, %s, %s, %s, %s::uuid[], %s::uuid[])""",
                    (group, index, int(len(in_type)), description["more"], description["less"],
                     [members.iloc[i]["player_id"] for i in closest], [members.iloc[i]["season_id"] for i in closest]),
                )
            with cur.copy("""COPY player_archetypes (player_id, season_id, position_group, archetype_index, distance,
                             second_index, second_distance) FROM STDIN""") as copy:
                for row, ranks, dists in zip(members.itertuples(), order, distances):
                    second = len(ranks) > 1
                    copy.write_row((row.player_id, row.season_id, group, int(ranks[0]), float(dists[0]),
                                    int(ranks[1]) if second else None, float(dists[1]) if second else None))
                    assigned += 1
    return assigned
