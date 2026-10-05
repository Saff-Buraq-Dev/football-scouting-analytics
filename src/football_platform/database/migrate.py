"""Minimal SQL migration runner (decision D015).

Migrations are plain SQL files named NNNN_description.sql in migrations/.
Each runs once, in its own transaction, and is recorded with a checksum.
Editing an already-applied migration is refused: write a new one instead.

Usage: python -m football_platform.database.migrate
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from importlib import resources

import psycopg

from football_platform.database.connection import connect

MIGRATION_NAME = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")


@dataclass(frozen=True, slots=True)
class Migration:
    version: str
    name: str
    sql: str

    @property
    def checksum(self) -> str:
        return hashlib.sha256(self.sql.encode("utf-8")).hexdigest()


class MigrationError(RuntimeError):
    pass


def discover_migrations() -> list[Migration]:
    folder = resources.files(__package__).joinpath("migrations")
    migrations = []
    for entry in folder.iterdir():
        if not entry.name.endswith(".sql"):
            continue
        match = MIGRATION_NAME.match(entry.name)
        if not match:
            raise MigrationError(f"Badly named migration file: {entry.name}")
        migrations.append(Migration(match.group(1), entry.name, entry.read_text(encoding="utf-8")))
    migrations.sort(key=lambda m: m.version)
    versions = [m.version for m in migrations]
    if len(versions) != len(set(versions)):
        raise MigrationError(f"Duplicate migration versions: {versions}")
    return migrations


def apply_migrations(conn: psycopg.Connection) -> list[str]:
    """Apply pending migrations. Returns the names of migrations applied now."""
    with conn.transaction():
        conn.execute(
            """CREATE TABLE IF NOT EXISTS schema_migrations (
                   version text PRIMARY KEY,
                   name text NOT NULL,
                   checksum text NOT NULL,
                   applied_at timestamptz NOT NULL DEFAULT now())"""
        )
    applied = {
        version: checksum
        for version, checksum in conn.execute("SELECT version, checksum FROM schema_migrations").fetchall()
    }
    newly_applied = []
    for migration in discover_migrations():
        if migration.version in applied:
            if applied[migration.version] != migration.checksum:
                raise MigrationError(f"{migration.name} changed after being applied; add a new migration instead")
            continue
        with conn.transaction():
            conn.execute(migration.sql)
            conn.execute(
                "INSERT INTO schema_migrations (version, name, checksum) VALUES (%s, %s, %s)",
                (migration.version, migration.name, migration.checksum),
            )
        newly_applied.append(migration.name)
    return newly_applied


def main() -> None:
    with connect(autocommit=True) as conn:
        applied = apply_migrations(conn)
    print("Applied: " + ", ".join(applied) if applied else "Database schema is up to date")


if __name__ == "__main__":
    main()
