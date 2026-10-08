"""Team-season report: database -> team analytics -> snapshot + files.

Usage:
    python -m football_platform.reports.team_season_report [--no-store]
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass

import pandas as pd
import psycopg

from football_platform.analytics.possession import team_match_possession
from football_platform.analytics.team import (
    TEAM_EVENT_COLUMNS,
    add_team_percentiles,
    team_match_stats,
    team_season_stats,
)
from football_platform.canonical.capabilities import ProviderCapabilities
from football_platform.canonical.enums import CoverageScope, EventType
from football_platform.database.connection import connect
from football_platform.database.migrate import apply_migrations
from football_platform.reports.player_season_report import OUTPUT_DIR, load_capabilities, query_frame
from football_platform.reports.snapshot import store_team_snapshot

TEAM_EVENT_TYPES = [EventType.PASS, EventType.SHOT, EventType.DUEL, EventType.INTERCEPTION, EventType.FOUL_COMMITTED,
                    EventType.BALL_RECOVERY]


@dataclass
class TeamInputs:
    capabilities: ProviderCapabilities
    events: pd.DataFrame
    metrics: pd.DataFrame
    matches: pd.DataFrame
    seasons: pd.DataFrame


def load_team_inputs(conn: psycopg.Connection) -> TeamInputs:
    types = ", ".join(f"'{t.value}'" for t in TEAM_EVENT_TYPES)
    return TeamInputs(
        capabilities=load_capabilities(conn),
        events=query_frame(conn, f"SELECT {', '.join(TEAM_EVENT_COLUMNS)} FROM events WHERE type IN ({types})"),
        metrics=query_frame(
            conn, "SELECT event_id, metric_key, value, source_provider, model_version FROM provider_metrics"
        ),
        matches=query_frame(
            conn, "SELECT id, season_id, match_date, home_team_id, away_team_id, home_score, away_score FROM matches"
        ),
        seasons=query_frame(conn, "SELECT id, label, coverage_scope FROM seasons"),
    )


def compute_teams(inputs: TeamInputs, match_ids: set[str] | None = None) -> pd.DataFrame:
    events, matches = inputs.events, inputs.matches
    if match_ids is not None:
        events = events[events["match_id"].isin(match_ids)]
        matches = matches[matches["id"].isin(match_ids)]
    team_match = team_match_stats(events, inputs.metrics, matches)
    season = team_season_stats(team_match, inputs.capabilities, team_match_possession(events))
    complete = inputs.seasons.loc[inputs.seasons["coverage_scope"] == CoverageScope.COMPLETE.value, "id"].tolist()
    return add_team_percentiles(season, [s for s in complete if s in set(season["season_id"])])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-store", action="store_true", help="do not replace the database snapshot")
    args = parser.parse_args()

    with connect(autocommit=True) as conn:
        apply_migrations(conn)
        report = compute_teams(load_team_inputs(conn))
        names = query_frame(conn, "SELECT id AS team_id, name AS team FROM teams")
        report = report.merge(names, on="team_id")
        stored = None
        if not args.no_store:
            stored = store_team_snapshot(conn, report)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report.to_csv(OUTPUT_DIR / "team_seasons.csv", index=False)
    print(json.dumps({"team_seasons": len(report), "stored": stored}, indent=2))


if __name__ == "__main__":
    main()
