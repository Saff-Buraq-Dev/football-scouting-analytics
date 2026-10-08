"""Recruitment board API against a temporary PostgreSQL database, with two users to check isolation."""

import uuid

import psycopg
import pytest
from fastapi.testclient import TestClient

from football_platform.api.app import create_app
from football_platform.auth.providers import AuthenticationError, DisabledAuthProvider, Identity
from football_platform.database.migrate import apply_migrations

pytestmark = pytest.mark.db


class HeaderAuth:
    """Test provider: "Bearer <name>" is user <name>."""

    mode = "test"

    def authenticate(self, authorization):
        if not authorization or not authorization.startswith("Bearer "):
            raise AuthenticationError("Missing bearer token")
        name = authorization.removeprefix("Bearer ")
        return Identity(issuer="test", subject=name, email=f"{name}@example.com", name=name.title())

    def public_config(self):
        return {"mode": self.mode}


ALICE = {"Authorization": "Bearer alice"}
BOB = {"Authorization": "Bearer bob"}


@pytest.fixture(scope="module")
def ids(test_database_url):
    """One competition, season and player: the board only references canonical rows."""
    competition, season, player = (str(uuid.uuid4()) for _ in range(3))
    with psycopg.connect(test_database_url, autocommit=True) as conn:
        apply_migrations(conn)
        conn.execute("""INSERT INTO competitions (id, name, area, gender, competition_type)
                        VALUES (%s, 'Test League', 'Nowhere', 'male', 'league')""", (competition,))
        conn.execute("""INSERT INTO seasons (id, competition_id, label, coverage_scope, has_events, has_lineups,
                        has_freeze_frames) VALUES (%s, %s, '2015/2016', 'complete', true, true, false)""",
                     (season, competition))
        conn.execute("INSERT INTO players (id, name) VALUES (%s, 'Board Test Player')", (player,))
    yield {"season": season, "player": player}
    # The test database is shared by the session: leave it as found (other tests count players).
    with psycopg.connect(test_database_url, autocommit=True) as conn:
        conn.execute("DELETE FROM app_users WHERE issuer = 'test'")  # cascades to shortlists, tags, notes
        conn.execute("DELETE FROM players WHERE id = %s", (player,))
        conn.execute("DELETE FROM seasons WHERE id = %s", (season,))
        conn.execute("DELETE FROM competitions WHERE id = %s", (competition,))


@pytest.fixture(scope="module")
def client(test_database_url, ids):
    return TestClient(create_app(test_database_url, auth=HeaderAuth()))


def test_requests_without_credentials_are_401(client):
    response = client.get("/api/shortlists")
    assert response.status_code == 401 and response.headers["www-authenticate"] == "Bearer"


def test_board_is_503_when_no_identity_provider_is_configured(test_database_url, ids):
    disabled = TestClient(create_app(test_database_url, auth=DisabledAuthProvider()))
    assert disabled.get("/api/shortlists").status_code == 503
    assert disabled.get("/api/auth/config").json() == {"mode": "disabled"}


def test_me_creates_the_user_once(client):
    first = client.get("/api/me", headers=ALICE).json()
    assert first["name"] == "Alice" and client.get("/api/me", headers=ALICE).json()["id"] == first["id"]


def test_shortlist_lifecycle(client, ids):
    created = client.post("/api/shortlists", json={"name": " Left-backs 2016 ", "description": "Summer"}, headers=ALICE)
    assert created.status_code == 201 and created.json()["name"] == "Left-backs 2016"
    sid = created.json()["id"]
    entry = f"/api/shortlists/{sid}/entries/{ids['player']}/{ids['season']}"
    assert client.put(entry, headers=ALICE).status_code == 204
    assert client.put(entry, headers=ALICE).status_code == 204  # idempotent
    rows = client.get(f"/api/shortlists/{sid}/entries", headers=ALICE).json()
    assert [r["player_name"] for r in rows] == ["Board Test Player"]
    assert rows[0]["minutes"] is None  # no analytics snapshot for this season: shown as unknown, not 0
    assert client.get("/api/shortlists", headers=ALICE).json()[0]["size"] == 1
    renamed = client.patch(f"/api/shortlists/{sid}", json={"name": "Left-backs"}, headers=ALICE).json()
    assert renamed["name"] == "Left-backs" and renamed["description"] == "Summer"
    assert client.delete(entry, headers=ALICE).status_code == 204
    assert client.delete(f"/api/shortlists/{sid}", headers=ALICE).status_code == 204
    assert client.get(f"/api/shortlists/{sid}/entries", headers=ALICE).status_code == 404


def test_duplicate_and_invalid_names(client):
    assert client.post("/api/shortlists", json={"name": "Strikers"}, headers=ALICE).status_code == 201
    assert client.post("/api/shortlists", json={"name": "Strikers"}, headers=ALICE).status_code == 409
    assert client.post("/api/shortlists", json={"name": "Strikers"}, headers=BOB).status_code == 201  # per user
    assert client.post("/api/shortlists", json={"name": "   "}, headers=ALICE).status_code == 422
    assert client.post("/api/shortlists", json={"name": "x" * 81}, headers=ALICE).status_code == 422


def test_unknown_player_is_404(client, ids):
    sid = client.post("/api/shortlists", json={"name": "Unknowns"}, headers=ALICE).json()["id"]
    missing = str(uuid.uuid4())
    assert client.put(f"/api/shortlists/{sid}/entries/{missing}/{ids['season']}", headers=ALICE).status_code == 404
    assert client.put(f"/api/players/{missing}/tags/fast", headers=ALICE).status_code == 404


def test_tags_and_notes(client, ids):
    player = ids["player"]
    assert client.put(f"/api/players/{player}/tags/ Left  Foot", headers=ALICE).json() == {"tag": "left foot"}
    note = client.post(f"/api/players/{player}/notes", json={"body": "Watched live: quick recovery runs.",
                                                            "season_id": ids["season"]}, headers=ALICE).json()
    assert note["season_label"] == "2015/2016"
    board = client.get(f"/api/players/{player}/board", headers=ALICE).json()
    assert board["tags"] == ["left foot"] and [n["id"] for n in board["notes"]] == [note["id"]]
    assert client.get("/api/tags", headers=ALICE).json() == [{"tag": "left foot", "players": 1}]
    edited = client.patch(f"/api/notes/{note['id']}", json={"body": "Edited"}, headers=ALICE).json()
    assert edited["body"] == "Edited"
    assert client.post(f"/api/players/{player}/notes", json={"body": ""}, headers=ALICE).status_code == 422
    assert client.delete(f"/api/players/{player}/tags/LEFT FOOT", headers=ALICE).status_code == 204
    assert client.delete(f"/api/notes/{note['id']}", headers=ALICE).status_code == 204


def test_users_never_see_or_change_each_others_data(client, ids):
    player = ids["player"]
    sid = client.post("/api/shortlists", json={"name": "Private"}, headers=ALICE).json()["id"]
    client.put(f"/api/shortlists/{sid}/entries/{player}/{ids['season']}", headers=ALICE)
    client.put(f"/api/players/{player}/tags/secret", headers=ALICE)
    note = client.post(f"/api/players/{player}/notes", json={"body": "Alice only"}, headers=ALICE).json()

    assert "Private" not in [s["name"] for s in client.get("/api/shortlists", headers=BOB).json()]
    assert client.get(f"/api/shortlists/{sid}/entries", headers=BOB).status_code == 404
    assert client.put(f"/api/shortlists/{sid}/entries/{player}/{ids['season']}", headers=BOB).status_code == 404
    assert client.delete(f"/api/shortlists/{sid}/entries/{player}/{ids['season']}", headers=BOB).status_code == 404
    assert client.patch(f"/api/shortlists/{sid}", json={"name": "Mine"}, headers=BOB).status_code == 404
    assert client.delete(f"/api/shortlists/{sid}", headers=BOB).status_code == 404
    assert client.patch(f"/api/notes/{note['id']}", json={"body": "x"}, headers=BOB).status_code == 404
    assert client.delete(f"/api/notes/{note['id']}", headers=BOB).status_code == 404
    assert client.get(f"/api/players/{player}/board", headers=BOB).json() == {"shortlists": [], "tags": [], "notes": []}
    # Alice's data is intact.
    board = client.get(f"/api/players/{player}/board", headers=ALICE).json()
    assert board["tags"] == ["secret"] and board["notes"][0]["body"] == "Alice only"
    assert [s["name"] for s in board["shortlists"]] == ["Private"]
