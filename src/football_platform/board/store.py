"""SQL access to board data. Every query is scoped to one owner: a user never reads or changes another's data.

Rows that do not exist and rows owned by someone else are indistinguishable (both return None / False),
so the API answers 404 in both cases and does not reveal other users' ids.
"""

from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import dict_row

from football_platform.board.rules import (
    MAX_DESCRIPTION, MAX_NOTE, MAX_SHORTLIST_NAME, InvalidBoardInputError, clean_text, normalise_tag,
)


class DuplicateNameError(InvalidBoardInputError):
    pass


def _rows(conn: psycopg.Connection, query: str, params: tuple = ()) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)
        return [{k: str(v) if k.endswith("id") and v is not None else v for k, v in r.items()} for r in cur.fetchall()]


def _one(conn: psycopg.Connection, query: str, params: tuple = ()) -> dict[str, Any] | None:
    rows = _rows(conn, query, params)
    return rows[0] if rows else None


# ---- Users --------------------------------------------------------------------------------------

def upsert_user(conn: psycopg.Connection, issuer: str, subject: str, email: str | None, name: str | None) -> dict:
    """The local user row of an identity, created on first sight and refreshed on every request."""
    row = _one(conn, """
        INSERT INTO app_users (issuer, subject, email, display_name) VALUES (%s, %s, %s, %s)
        ON CONFLICT (issuer, subject) DO UPDATE SET
            email = coalesce(EXCLUDED.email, app_users.email),
            display_name = coalesce(EXCLUDED.display_name, app_users.display_name),
            last_seen_at = now()
        RETURNING id, email, display_name""", (issuer, subject, email, name))
    assert row is not None
    return row


# ---- Shortlists ---------------------------------------------------------------------------------

def list_shortlists(conn: psycopg.Connection, owner_id: str) -> list[dict]:
    return _rows(conn, """
        SELECT s.id, s.name, s.description, s.created_at, s.updated_at,
               (SELECT count(*) FROM shortlist_entries e WHERE e.shortlist_id = s.id) AS size
        FROM shortlists s WHERE s.owner_id = %s ORDER BY s.name""", (owner_id,))


def create_shortlist(conn: psycopg.Connection, owner_id: str, name: str, description: str = "") -> dict:
    name = clean_text(name, "Name", MAX_SHORTLIST_NAME)
    description = clean_text(description, "Description", MAX_DESCRIPTION, required=False)
    try:
        row = _one(conn, """INSERT INTO shortlists (owner_id, name, description) VALUES (%s, %s, %s)
                            RETURNING id, name, description, created_at, updated_at, 0 AS size""",
                   (owner_id, name, description))
    except psycopg.errors.UniqueViolation:
        raise DuplicateNameError(f"You already have a shortlist named {name!r}") from None
    assert row is not None
    return row


def update_shortlist(conn: psycopg.Connection, owner_id: str, shortlist_id: str,
                     name: str | None, description: str | None) -> dict | None:
    current = _one(conn, "SELECT name, description FROM shortlists WHERE id = %s AND owner_id = %s",
                   (shortlist_id, owner_id))
    if current is None:
        return None
    new_name = clean_text(name, "Name", MAX_SHORTLIST_NAME) if name is not None else current["name"]
    new_description = (clean_text(description, "Description", MAX_DESCRIPTION, required=False)
                       if description is not None else current["description"])
    try:
        return _one(conn, """
            UPDATE shortlists SET name = %s, description = %s, updated_at = now()
            WHERE id = %s AND owner_id = %s
            RETURNING id, name, description, created_at, updated_at,
                      (SELECT count(*) FROM shortlist_entries e WHERE e.shortlist_id = shortlists.id) AS size""",
            (new_name, new_description, shortlist_id, owner_id))
    except psycopg.errors.UniqueViolation:
        raise DuplicateNameError(f"You already have a shortlist named {new_name!r}") from None


def delete_shortlist(conn: psycopg.Connection, owner_id: str, shortlist_id: str) -> bool:
    return conn.execute("DELETE FROM shortlists WHERE id = %s AND owner_id = %s",
                        (shortlist_id, owner_id)).rowcount == 1


def shortlist_entries(conn: psycopg.Connection, owner_id: str, shortlist_id: str) -> list[dict] | None:
    """Entries with player and season context; analytics fields are null when the season is not in the snapshot."""
    if _one(conn, "SELECT 1 AS ok FROM shortlists WHERE id = %s AND owner_id = %s", (shortlist_id, owner_id)) is None:
        return None
    return _rows(conn, """
        SELECT e.player_id, e.season_id, e.added_at,
               coalesce(p.known_name, p.name) AS player_name,
               s.label AS season_label, c.name AS competition,
               ps.minutes, ps.position_group, ps.primary_role, ps.eligible,
               (SELECT array_agg(t.name ORDER BY t.name) FROM teams t WHERE t.id = ANY(ps.team_ids)) AS teams,
               coalesce((SELECT array_agg(pt.tag ORDER BY pt.tag) FROM player_tags pt
                         WHERE pt.owner_id = %s AND pt.player_id = e.player_id), '{}') AS tags,
               (SELECT count(*) FROM player_notes n WHERE n.owner_id = %s AND n.player_id = e.player_id) AS notes
        FROM shortlist_entries e
        JOIN players p ON p.id = e.player_id
        JOIN seasons s ON s.id = e.season_id
        JOIN competitions c ON c.id = s.competition_id
        LEFT JOIN player_seasons ps ON ps.player_id = e.player_id AND ps.season_id = e.season_id
        WHERE e.shortlist_id = %s
        ORDER BY e.added_at""", (owner_id, owner_id, shortlist_id))


def add_entry(conn: psycopg.Connection, owner_id: str, shortlist_id: str, player_id: str, season_id: str) -> bool:
    """False when the shortlist is not the owner's. Adding twice is harmless (idempotent)."""
    if _one(conn, "SELECT 1 AS ok FROM shortlists WHERE id = %s AND owner_id = %s", (shortlist_id, owner_id)) is None:
        return False
    conn.execute("""INSERT INTO shortlist_entries (shortlist_id, player_id, season_id) VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING""", (shortlist_id, player_id, season_id))
    conn.execute("UPDATE shortlists SET updated_at = now() WHERE id = %s", (shortlist_id,))
    return True


def remove_entry(conn: psycopg.Connection, owner_id: str, shortlist_id: str, player_id: str, season_id: str) -> bool:
    return conn.execute("""
        DELETE FROM shortlist_entries e USING shortlists s
        WHERE e.shortlist_id = s.id AND s.id = %s AND s.owner_id = %s AND e.player_id = %s AND e.season_id = %s""",
        (shortlist_id, owner_id, player_id, season_id)).rowcount == 1


# ---- Tags and notes -----------------------------------------------------------------------------

def list_tags(conn: psycopg.Connection, owner_id: str) -> list[dict]:
    return _rows(conn, """SELECT tag, count(*) AS players FROM player_tags WHERE owner_id = %s
                          GROUP BY tag ORDER BY tag""", (owner_id,))


def add_tag(conn: psycopg.Connection, owner_id: str, player_id: str, tag: str) -> str:
    tag = normalise_tag(tag)
    conn.execute("""INSERT INTO player_tags (owner_id, player_id, tag) VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING""", (owner_id, player_id, tag))
    return tag


def remove_tag(conn: psycopg.Connection, owner_id: str, player_id: str, tag: str) -> bool:
    return conn.execute("DELETE FROM player_tags WHERE owner_id = %s AND player_id = %s AND tag = %s",
                        (owner_id, player_id, normalise_tag(tag))).rowcount == 1


NOTE_COLUMNS = """n.id, n.player_id, n.season_id, s.label AS season_label, n.body, n.created_at, n.updated_at"""


def add_note(conn: psycopg.Connection, owner_id: str, player_id: str, body: str, season_id: str | None) -> dict:
    body = clean_text(body, "Note", MAX_NOTE)
    row = _one(conn, f"""
        WITH n AS (INSERT INTO player_notes (owner_id, player_id, season_id, body) VALUES (%s, %s, %s, %s)
                   RETURNING *)
        SELECT {NOTE_COLUMNS} FROM n LEFT JOIN seasons s ON s.id = n.season_id""",
        (owner_id, player_id, season_id, body))
    assert row is not None
    return row


def update_note(conn: psycopg.Connection, owner_id: str, note_id: str, body: str) -> dict | None:
    body = clean_text(body, "Note", MAX_NOTE)
    return _one(conn, f"""
        WITH n AS (UPDATE player_notes SET body = %s, updated_at = now() WHERE id = %s AND owner_id = %s
                   RETURNING *)
        SELECT {NOTE_COLUMNS} FROM n LEFT JOIN seasons s ON s.id = n.season_id""", (body, note_id, owner_id))


def delete_note(conn: psycopg.Connection, owner_id: str, note_id: str) -> bool:
    return conn.execute("DELETE FROM player_notes WHERE id = %s AND owner_id = %s",
                        (note_id, owner_id)).rowcount == 1


def player_board(conn: psycopg.Connection, owner_id: str, player_id: str) -> dict:
    """Everything the owner has on one player: shortlist memberships, tags, notes (newest first)."""
    memberships = _rows(conn, """
        SELECT s.id AS shortlist_id, s.name, e.season_id FROM shortlist_entries e JOIN shortlists s ON s.id = e.shortlist_id
        WHERE s.owner_id = %s AND e.player_id = %s ORDER BY s.name""", (owner_id, player_id))
    tags = [r["tag"] for r in _rows(conn, """SELECT tag FROM player_tags WHERE owner_id = %s AND player_id = %s
                                              ORDER BY tag""", (owner_id, player_id))]
    notes = _rows(conn, f"""SELECT {NOTE_COLUMNS} FROM player_notes n LEFT JOIN seasons s ON s.id = n.season_id
                            WHERE n.owner_id = %s AND n.player_id = %s ORDER BY n.created_at DESC""",
                  (owner_id, player_id))
    return {"shortlists": memberships, "tags": tags, "notes": notes}
