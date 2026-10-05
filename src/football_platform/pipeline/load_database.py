"""Load a canonical Parquet output (from pipeline.ingest) into PostgreSQL.

Semantics (decision D015):
- one transaction: a failed load leaves the database unchanged;
- reference entities (competitions, seasons, teams, players, external ids) are
  upserted;
- match content is replaced: loaded matches are deleted first (cascading to
  appearances, spells, events, metrics), then re-inserted, so reloading the
  same output is idempotent;
- after loading, row counts in the database are checked against the Parquet files.

Usage:
    python -m football_platform.pipeline.load_database [CANONICAL_DIR]
Default CANONICAL_DIR: most recent folder under data/canonical/statsbomb_open/.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Iterator

import psycopg
import pyarrow.parquet as pq
from psycopg import sql

from football_platform.database.connection import connect
from football_platform.database.migrate import apply_migrations

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CANONICAL_ROOT = PROJECT_ROOT / "data" / "canonical"
BATCH_ROWS = 50_000

UPSERT_TABLES = ("competitions", "seasons", "teams", "players")
MATCH_CONTENT_TABLES = ("matches", "appearances", "position_spells", "events", "provider_metrics")

logger = logging.getLogger("football_platform.load_database")


class LoadVerificationError(RuntimeError):
    pass


def _rows(path: Path) -> Iterator[tuple[list[str], list[tuple]]]:
    """Yield (column names, row tuples) batches from a Parquet file."""
    parquet = pq.ParquetFile(path)
    for batch in parquet.iter_batches(batch_size=BATCH_ROWS):
        columns = [batch.column(i).to_pylist() for i in range(batch.num_columns)]
        yield batch.schema.names, list(zip(*columns))


def copy_parquet(cur: psycopg.Cursor, path: Path, table: str) -> int:
    """COPY a Parquet file into a table whose columns have the same names."""
    names = pq.ParquetFile(path).schema_arrow.names
    statement = sql.SQL("COPY {} ({}) FROM STDIN").format(
        sql.Identifier(table), sql.SQL(", ").join(map(sql.Identifier, names))
    )
    count = 0
    with cur.copy(statement) as copy:
        for _, rows in _rows(path):
            for row in rows:
                copy.write_row(row)
            count += len(rows)
    return count


def upsert_parquet(cur: psycopg.Cursor, path: Path, table: str, key: tuple[str, ...]) -> int:
    names = pq.ParquetFile(path).schema_arrow.names
    staging = f"staging_{table}"
    cur.execute(
        sql.SQL("CREATE TEMP TABLE {} (LIKE {}) ON COMMIT DROP").format(
            sql.Identifier(staging), sql.Identifier(table)
        )
    )
    count = copy_parquet(cur, path, staging)
    updates = [n for n in names if n not in key]
    on_conflict = (
        sql.SQL("DO UPDATE SET {}").format(
            sql.SQL(", ").join(sql.SQL("{0} = EXCLUDED.{0}").format(sql.Identifier(n)) for n in updates)
        )
        if updates
        else sql.SQL("DO NOTHING")
    )
    cur.execute(
        sql.SQL("INSERT INTO {t} ({cols}) SELECT {cols} FROM {s} ON CONFLICT ({key}) {action}").format(
            t=sql.Identifier(table),
            s=sql.Identifier(staging),
            cols=sql.SQL(", ").join(map(sql.Identifier, names)),
            key=sql.SQL(", ").join(map(sql.Identifier, key)),
            action=on_conflict,
        )
    )
    return count


def _parquet_rows(directory: Path, table: str) -> int:
    return pq.ParquetFile(directory / f"{table}.parquet").metadata.num_rows


def load(canonical_dir: Path, conn: psycopg.Connection) -> dict[str, int]:
    manifest = json.loads((canonical_dir / "manifest.json").read_text(encoding="utf-8"))
    match_ids = pq.read_table(canonical_dir / "matches.parquet", columns=["id"]).column("id").to_pylist()

    with conn.transaction(), conn.cursor() as cur:
        cur.execute(
            """INSERT INTO ingestion_runs (id, provider, source_release, started_utc, finished_utc, manifest)
               VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING""",
            (manifest["ingestion_run_id"], manifest["provider"], manifest["source_release"],
             manifest["started_utc"], manifest["finished_utc"], json.dumps(manifest)),
        )
        for table in UPSERT_TABLES:
            upsert_parquet(cur, canonical_dir / f"{table}.parquet", table, ("id",))
            logger.info("Upserted %s", table)

        cur.execute("DELETE FROM matches WHERE id = ANY(%s::uuid[])", (match_ids,))
        if cur.rowcount:
            logger.info("Replacing %d previously loaded matches", cur.rowcount)
        for table in MATCH_CONTENT_TABLES:
            count = copy_parquet(cur, canonical_dir / f"{table}.parquet", table)
            logger.info("Loaded %s: %d rows", table, count)

        upsert_parquet(cur, canonical_dir / "external_ids.parquet", "external_ids",
                       ("provider", "entity_type", "provider_id"))

        counts = verify_counts(cur, canonical_dir, match_ids)
    return counts


def verify_counts(cur: psycopg.Cursor, canonical_dir: Path, match_ids: list[str]) -> dict[str, int]:
    """Database rows for the loaded matches must equal the Parquet row counts."""
    counts = {}
    for table in MATCH_CONTENT_TABLES:
        column = "id" if table == "matches" else "match_id"
        cur.execute(
            sql.SQL("SELECT count(*) FROM {} WHERE {} = ANY(%s::uuid[])").format(
                sql.Identifier(table), sql.Identifier(column)
            ),
            (match_ids,),
        )
        in_db = cur.fetchone()[0]
        expected = _parquet_rows(canonical_dir, table)
        if in_db != expected:
            raise LoadVerificationError(f"{table}: {in_db} rows in database, {expected} in Parquet")
        counts[table] = in_db
    return counts


def latest_canonical_dir(root: Path = DEFAULT_CANONICAL_ROOT) -> Path:
    candidates = sorted(root.glob("*/*/manifest.json"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        raise FileNotFoundError(f"No canonical output under {root}; run pipeline.ingest first")
    return candidates[-1].parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("canonical_dir", nargs="?", type=Path)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    canonical_dir = args.canonical_dir or latest_canonical_dir()
    with connect() as conn:
        apply_migrations(conn)
        counts = load(canonical_dir, conn)
    print(json.dumps({"loaded_from": str(canonical_dir), "row_counts": counts}, indent=2))


if __name__ == "__main__":
    main()
