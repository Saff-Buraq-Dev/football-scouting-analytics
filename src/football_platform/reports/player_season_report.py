"""Player-season report: database -> analytics -> Parquet/CSV, plus a console summary.

Usage:
    python -m football_platform.reports.player_season_report [--min-minutes 900]

Output (gitignored, derived from licensed data): data/analytics/player_seasons.{parquet,csv}
"""

from __future__ import annotations

import argparse
import io
import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import psycopg

from football_platform.analytics.definitions import DEFAULT_MIN_MINUTES
from football_platform.analytics.percentiles import add_percentiles
from football_platform.analytics.player_match import EVENT_COLUMNS, player_match_stats
from football_platform.analytics.player_season import player_season_stats
from football_platform.analytics.possession import team_match_possession
from football_platform.analytics.shrinkage import add_regressed_estimates
from football_platform.canonical.capabilities import ProviderCapabilities
from football_platform.canonical.enums import CoverageScope, EventType
from football_platform.database.connection import connect
from football_platform.database.migrate import apply_migrations
from football_platform.reports.snapshot import store_snapshot

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = PROJECT_ROOT / "data" / "analytics"

# Event types used by the v1 metrics (plus any event flagged as an aerial win).
METRIC_EVENT_TYPES = [
    EventType.PASS, EventType.SHOT, EventType.CARRY, EventType.DUEL,
    EventType.INTERCEPTION, EventType.BALL_RECOVERY, EventType.PRESSURE, EventType.GOALKEEPER_ACTION,
]


def query_frame(conn: psycopg.Connection, query: str) -> pd.DataFrame:
    """Run a SELECT through COPY ... TO STDOUT (fast for millions of rows)."""
    buffer = io.BytesIO()
    with conn.cursor() as cur, cur.copy(f"COPY ({query}) TO STDOUT WITH (FORMAT csv, HEADER)") as copy:
        for chunk in copy:
            buffer.write(chunk)
    buffer.seek(0)
    return pd.read_csv(buffer, true_values=["t"], false_values=["f"], low_memory=False)


def load_capabilities(conn: psycopg.Connection) -> ProviderCapabilities:
    providers = [r[0] for r in conn.execute("SELECT DISTINCT source_provider FROM events").fetchall()]
    if len(providers) != 1:
        raise ValueError(f"v1 report expects data from exactly one provider, found {providers}")
    row = conn.execute(
        """SELECT manifest->'capabilities' FROM ingestion_runs
           WHERE provider = %s AND manifest ? 'capabilities'
           ORDER BY loaded_at DESC LIMIT 1""",
        (providers[0],),
    ).fetchone()
    if row is None:
        raise ValueError(f"No capabilities recorded for {providers[0]}; re-run ingestion")
    return ProviderCapabilities.from_dict(row[0])


@dataclass
class ReportInputs:
    capabilities: ProviderCapabilities
    events: pd.DataFrame
    metrics: pd.DataFrame
    matches: pd.DataFrame
    appearances: pd.DataFrame
    spells: pd.DataFrame
    seasons: pd.DataFrame


def load_inputs(conn: psycopg.Connection) -> ReportInputs:
    types = ", ".join(f"'{t.value}'" for t in METRIC_EVENT_TYPES)
    return ReportInputs(
        capabilities=load_capabilities(conn),
        events=query_frame(
            conn, f"SELECT {', '.join(EVENT_COLUMNS)} FROM events WHERE type IN ({types}) OR aerial_won"
        ),
        metrics=query_frame(
            conn, "SELECT event_id, metric_key, value, source_provider, model_version FROM provider_metrics"
        ),
        matches=query_frame(conn, "SELECT id, season_id, match_date, home_team_id, away_team_id FROM matches"),
        appearances=query_frame(
            conn, "SELECT match_id, team_id, player_id, is_starter, minutes_played FROM appearances"
        ),
        spells=query_frame(
            conn, "SELECT match_id, team_id, player_id, period, start_s, end_s, role FROM position_spells"
        ),
        seasons=query_frame(
            conn,
            """SELECT s.id, s.label, s.coverage_scope, c.name AS competition
               FROM seasons s JOIN competitions c ON c.id = s.competition_id""",
        ),
    )


def compute(inputs: ReportInputs, min_minutes: float, match_ids: set[str] | None = None) -> pd.DataFrame:
    """Analytics pipeline on loaded inputs, optionally restricted to a subset of matches."""
    events, appearances, spells = inputs.events, inputs.appearances, inputs.spells
    if match_ids is not None:
        events = events[events["match_id"].isin(match_ids)]
        appearances = appearances[appearances["match_id"].isin(match_ids)]
        spells = spells[spells["match_id"].isin(match_ids)]
    per_match = player_match_stats(events, inputs.metrics, spells, inputs.matches)
    possession = team_match_possession(events)
    per_season = player_season_stats(
        per_match, appearances, spells, inputs.matches, inputs.capabilities, possession, min_minutes
    )
    seasons = inputs.seasons
    complete = seasons.loc[seasons["coverage_scope"] == CoverageScope.COMPLETE.value, "id"].tolist()
    return add_regressed_estimates(add_percentiles(per_season, seasons, complete), seasons, complete)


def build_report(conn: psycopg.Connection, min_minutes: float) -> pd.DataFrame:
    inputs = load_inputs(conn)
    report = compute(inputs, min_minutes)
    players = query_frame(conn, "SELECT id AS player_id, coalesce(known_name, name) AS player FROM players")
    teams = query_frame(conn, "SELECT id, name FROM teams").set_index("id")["name"]
    report = report.merge(players, on="player_id").merge(
        inputs.seasons.rename(columns={"id": "season_id", "label": "season"}), on="season_id"
    )
    report["teams"] = report["team_ids"].map(lambda ids: " / ".join(teams[i] for i in ids))
    return report


def print_summary(report: pd.DataFrame) -> None:
    headline = {
        "striker": "npxg_p90",
        "attacking_midfield_winger": "xa_p90",
        "central_midfield": "progressive_passes_p90",
        "full_back": "passes_into_final_third_p90",
        "centre_back": "interceptions_p90",
        "goalkeeper": "gk_np_save_pct",
    }
    eligible = report[report["eligible"]]
    print(f"Eligible player-seasons (>= {report['min_minutes'].iloc[0]:.0f} min): {len(eligible)} of {len(report)}")
    for group, metric in headline.items():
        ranked = eligible[(eligible["position_group"] == group) & eligible[metric + "_pct"].notna()]
        top = ranked.nlargest(5, metric)
        print(f"\nTop {group.replace('_', ' ')} by {metric} (population {int(top['population_size'].iloc[0])}):")
        for _, r in top.iterrows():
            print(f"  {r['player']:<26} {r['teams']:<22} {r['competition']:<15} "
                  f"{r[metric]:6.2f}  pct {r[metric + '_pct']:5.1f}  ({r['minutes']:.0f} min, "
                  f"team poss {r['team_possession_pct']:.0f} %)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--min-minutes", type=float, default=DEFAULT_MIN_MINUTES)
    parser.add_argument("--no-store", action="store_true", help="do not replace the database snapshot")
    args = parser.parse_args()

    # Autocommit: each `conn.transaction()` block is then an independent transaction.
    with connect(autocommit=True) as conn:
        apply_migrations(conn)
        report = build_report(conn, args.min_minutes)
        run_id = None
        if not args.no_store:
            run_id = store_snapshot(
                conn, report, args.min_minutes, sorted(report["population_seasons"].iloc[0].split(",")),
                report["source_provider"].iloc[0],
            )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    files = report.assign(team_ids=report["team_ids"].map(list))
    files.to_parquet(OUTPUT_DIR / "player_seasons.parquet", index=False)
    files.to_csv(OUTPUT_DIR / "player_seasons.csv", index=False)
    print_summary(report)
    print(json.dumps({"rows": len(report), "output": str(OUTPUT_DIR), "analytics_run_id": run_id}, indent=2))


if __name__ == "__main__":
    main()
