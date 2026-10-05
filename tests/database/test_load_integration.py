"""End to end: synthetic StatsBomb files -> ingestion -> Parquet -> PostgreSQL."""

import psycopg
import pytest

from football_platform.database.migrate import apply_migrations
from football_platform.pipeline.ingest import run as ingest
from football_platform.pipeline.load_database import load
from tests.providers.statsbomb.factories import write_synthetic_raw_store

pytestmark = pytest.mark.db

COMMIT = "synthetic0commit"


@pytest.fixture
def canonical_dir(tmp_path):
    raw_root = tmp_path / "raw"
    write_synthetic_raw_store(raw_root, COMMIT)
    (raw_root / "PINNED_COMMIT").write_text(COMMIT)
    manifest = ingest([(2, 27)], raw_root, tmp_path / "canonical", download=False)
    # The fixture fields one player per team, so only the score check is expected to pass.
    assert "score" not in manifest["validation_issues_by_check"]
    return tmp_path / "canonical" / COMMIT[:12]


def test_migrations_apply_once(db):
    apply_migrations(db)
    assert apply_migrations(db) == []


def test_load_and_reload_is_idempotent(db, canonical_dir):
    apply_migrations(db)
    first = load(canonical_dir, db)
    second = load(canonical_dir, db)
    assert first == second == {
        "matches": 1, "appearances": 2, "position_spells": 2, "events": 6, "provider_metrics": 1,
    }
    (players,) = db.execute("SELECT count(*) FROM players").fetchone()
    assert players == 2


def test_loaded_data_answers_football_questions(db, canonical_dir):
    apply_migrations(db)
    load(canonical_dir, db)
    row = db.execute(
        """SELECT round(sum(a.minutes_played)::numeric, 1), sum(pm.value)
           FROM appearances a
           JOIN events e ON e.player_id = a.player_id AND e.type = 'shot'
           JOIN provider_metrics pm ON pm.event_id = e.id AND pm.metric_key = 'xg'
           WHERE a.minutes_played > 0"""
    ).fetchone()
    assert row == (94.0, 0.3)


def test_schema_rejects_invalid_canonical_values(db):
    apply_migrations(db)
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute(
            "INSERT INTO competitions (id, name, area, gender, competition_type) "
            "VALUES (gen_random_uuid(), 'X', 'Y', 'mixed', 'league')"
        )
