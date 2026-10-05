"""Integration-test fixtures: a throw-away PostgreSQL database per test session.

Tests marked `db` are skipped when no server is reachable. They create a
temporary database on the configured server and drop it afterwards, so the
development database is never touched.
"""

import uuid

import psycopg
import pytest
from psycopg import sql

from football_platform.database.connection import DatabaseNotConfiguredError, database_url


def _server_url() -> str | None:
    try:
        url = database_url()
        with psycopg.connect(url, connect_timeout=2):
            return url
    except (DatabaseNotConfiguredError, psycopg.OperationalError):
        return None


@pytest.fixture(scope="session")
def test_database_url():
    url = _server_url()
    if url is None:
        pytest.skip("PostgreSQL not reachable (start it with `docker compose up -d`)")
    name = f"football_test_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(url, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    info = psycopg.conninfo.conninfo_to_dict(url)
    info["dbname"] = name
    yield psycopg.conninfo.make_conninfo(**info)
    with psycopg.connect(url, autocommit=True) as admin:
        admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


@pytest.fixture
def db(test_database_url):
    with psycopg.connect(test_database_url, autocommit=True) as conn:
        yield conn
