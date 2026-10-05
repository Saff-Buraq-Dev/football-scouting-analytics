"""Synthetic StatsBomb files -> ingestion -> PostgreSQL -> analytics snapshot -> HTTP API."""

import psycopg
import pytest
from fastapi.testclient import TestClient

from football_platform.api.app import create_app
from football_platform.database.migrate import apply_migrations
from football_platform.pipeline.ingest import run as ingest
from football_platform.pipeline.load_database import load
from football_platform.reports.player_season_report import build_report
from football_platform.reports.snapshot import store_snapshot
from tests.providers.statsbomb.factories import write_synthetic_raw_store

pytestmark = pytest.mark.db
COMMIT = "synthetic0commit"


@pytest.fixture(scope="module")
def client(test_database_url, tmp_path_factory):
    tmp = tmp_path_factory.mktemp("api")
    write_synthetic_raw_store(tmp / "raw", COMMIT)
    (tmp / "raw" / "PINNED_COMMIT").write_text(COMMIT)
    ingest([(2, 27)], tmp / "raw", tmp / "canonical", download=False)
    with psycopg.connect(test_database_url, autocommit=True) as conn:
        apply_migrations(conn)
        load(tmp / "canonical" / COMMIT[:12], conn)
        report = build_report(conn, 900.0)
        store_snapshot(conn, report, 900.0, list(report["season_id"].unique()), "statsbomb_open")
    return TestClient(create_app(test_database_url))


def test_health_reports_the_snapshot(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_search_is_accent_and_case_insensitive(client):
    results = client.get("/api/players", params={"q": "PLAYER 1"}).json()["results"]
    assert [r["player_name"] for r in results] == ["Player 1"]


def test_profile_of_a_player_below_the_threshold_is_explained_not_ranked(client):
    hit = client.get("/api/players", params={"q": "player 1"}).json()["results"][0]
    profile = client.get(f"/api/players/{hit['player_id']}/seasons/{hit['season_id']}").json()
    assert profile["playing_time"]["eligible"] is False
    npxg = next(m for t in profile["themes"] for m in t["metrics"] if m["key"] == "npxg")
    assert npxg["value"] == pytest.approx(0.3 / 94 * 90)
    assert npxg["percentile"] is None and npxg["percentile_note"] == "below_minutes_threshold"


def test_unknown_profile_is_404_and_bad_ids_are_422(client):
    assert client.get("/api/players/00000000-0000-0000-0000-000000000000/seasons/"
                      "00000000-0000-0000-0000-000000000000").status_code == 404
    assert client.get("/api/players/not-a-uuid/seasons/also-not").status_code == 422


def test_api_never_exposes_event_level_data(client):
    paths = set(client.get("/openapi.json").json()["paths"])
    assert not any("event" in p for p in paths)


def test_population_size_is_given_even_when_the_player_is_not_ranked(client):
    hit = client.get("/api/players", params={"q": "player 1"}).json()["results"][0]
    profile = client.get(f"/api/players/{hit['player_id']}/seasons/{hit['season_id']}").json()
    # The synthetic league has no eligible striker: an explicit 0, not a missing value.
    assert profile["population"]["size"] == 0


def test_compare_endpoint_validates_its_input(client):
    hit = client.get("/api/players", params={"q": "player 1"}).json()["results"][0]
    ref = f"{hit['player_id']}:{hit['season_id']}"
    assert client.get("/api/compare", params={"ps": [ref]}).status_code == 422
    assert client.get("/api/compare", params={"ps": [ref, ref]}).status_code == 422
    assert client.get("/api/compare", params={"ps": [ref, "bad:id"]}).status_code == 422
    missing = "00000000-0000-0000-0000-000000000000:00000000-0000-0000-0000-000000000000"
    assert client.get("/api/compare", params={"ps": [ref, missing]}).status_code == 404
