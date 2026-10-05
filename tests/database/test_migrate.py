from football_platform.database.migrate import discover_migrations


def test_migrations_are_ordered_and_start_with_canonical_schema():
    migrations = discover_migrations()
    assert [m.version for m in migrations] == sorted(m.version for m in migrations)
    assert migrations[0].name == "0001_canonical_schema.sql"
    assert len(migrations[0].checksum) == 64
