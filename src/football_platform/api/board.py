"""Recruitment board endpoints (Phase 11.9, D032): the only part of the API that needs a logged-in user.

Authentication is delegated to an AuthProvider (football_platform.auth): the routes only see a user id.
All data is private to its owner; another user's ids answer 404.
"""

# No `from __future__ import annotations`: FastAPI must resolve the Depends aliases defined in board_router.

from collections.abc import Callable, Iterator
from typing import Annotated, Any
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel

from football_platform.auth.providers import AuthenticationError, AuthNotConfiguredError, AuthProvider
from football_platform.board import store
from football_platform.board.rules import InvalidBoardInputError


class ShortlistIn(BaseModel):
    name: str
    description: str = ""


class ShortlistPatch(BaseModel):
    name: str | None = None
    description: str | None = None


class NoteIn(BaseModel):
    body: str
    season_id: UUID | None = None


class NotePatch(BaseModel):
    body: str


def _not_found(what: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{what} not found")


def board_router(auth: AuthProvider, connection: Callable[[], Iterator[psycopg.Connection]]) -> APIRouter:
    router = APIRouter(prefix="/api")
    Conn = Annotated[psycopg.Connection, Depends(connection)]

    def current_user(conn: Conn, authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
        try:
            identity = auth.authenticate(authorization)
        except AuthNotConfiguredError as error:
            raise HTTPException(status_code=503, detail=str(error)) from None
        except AuthenticationError as error:
            raise HTTPException(status_code=401, detail=str(error),
                                headers={"WWW-Authenticate": "Bearer"}) from None
        return store.upsert_user(conn, identity.issuer, identity.subject, identity.email, identity.name)

    User = Annotated[dict[str, Any], Depends(current_user)]

    def guarded(action: Callable[[], Any]) -> Any:
        """Translate input and reference errors into HTTP answers."""
        try:
            return action()
        except store.DuplicateNameError as error:
            raise HTTPException(status_code=409, detail=str(error)) from None
        except InvalidBoardInputError as error:
            raise HTTPException(status_code=422, detail=str(error)) from None
        except psycopg.errors.ForeignKeyViolation:
            raise _not_found("Player or season") from None

    @router.get("/auth/config")
    def auth_config() -> dict:
        return auth.public_config()

    @router.get("/me")
    def me(user: User) -> dict:
        return {"id": user["id"], "email": user["email"], "name": user["display_name"]}

    @router.get("/shortlists")
    def shortlists(conn: Conn, user: User) -> list[dict]:
        return store.list_shortlists(conn, user["id"])

    @router.post("/shortlists", status_code=201)
    def create_shortlist(conn: Conn, user: User, body: ShortlistIn) -> dict:
        return guarded(lambda: store.create_shortlist(conn, user["id"], body.name, body.description))

    @router.patch("/shortlists/{shortlist_id}")
    def update_shortlist(conn: Conn, user: User, shortlist_id: UUID, body: ShortlistPatch) -> dict:
        row = guarded(lambda: store.update_shortlist(conn, user["id"], str(shortlist_id), body.name, body.description))
        if row is None:
            raise _not_found("Shortlist")
        return row

    @router.delete("/shortlists/{shortlist_id}", status_code=204)
    def delete_shortlist(conn: Conn, user: User, shortlist_id: UUID) -> Response:
        if not store.delete_shortlist(conn, user["id"], str(shortlist_id)):
            raise _not_found("Shortlist")
        return Response(status_code=204)

    @router.get("/shortlists/{shortlist_id}/entries")
    def entries(conn: Conn, user: User, shortlist_id: UUID) -> list[dict]:
        rows = store.shortlist_entries(conn, user["id"], str(shortlist_id))
        if rows is None:
            raise _not_found("Shortlist")
        return rows

    @router.put("/shortlists/{shortlist_id}/entries/{player_id}/{season_id}", status_code=204)
    def add_entry(conn: Conn, user: User, shortlist_id: UUID, player_id: UUID, season_id: UUID) -> Response:
        if not guarded(lambda: store.add_entry(conn, user["id"], str(shortlist_id), str(player_id), str(season_id))):
            raise _not_found("Shortlist")
        return Response(status_code=204)

    @router.delete("/shortlists/{shortlist_id}/entries/{player_id}/{season_id}", status_code=204)
    def remove_entry(conn: Conn, user: User, shortlist_id: UUID, player_id: UUID, season_id: UUID) -> Response:
        if not store.remove_entry(conn, user["id"], str(shortlist_id), str(player_id), str(season_id)):
            raise _not_found("Entry")
        return Response(status_code=204)

    @router.get("/tags")
    def tags(conn: Conn, user: User) -> list[dict]:
        return store.list_tags(conn, user["id"])

    @router.get("/players/{player_id}/board")
    def player_board(conn: Conn, user: User, player_id: UUID) -> dict:
        return store.player_board(conn, user["id"], str(player_id))

    @router.put("/players/{player_id}/tags/{tag}")
    def add_tag(conn: Conn, user: User, player_id: UUID, tag: str) -> dict:
        return {"tag": guarded(lambda: store.add_tag(conn, user["id"], str(player_id), tag))}

    @router.delete("/players/{player_id}/tags/{tag}", status_code=204)
    def remove_tag(conn: Conn, user: User, player_id: UUID, tag: str) -> Response:
        if not guarded(lambda: store.remove_tag(conn, user["id"], str(player_id), tag)):
            raise _not_found("Tag")
        return Response(status_code=204)

    @router.post("/players/{player_id}/notes", status_code=201)
    def add_note(conn: Conn, user: User, player_id: UUID, body: NoteIn) -> dict:
        season = str(body.season_id) if body.season_id else None
        return guarded(lambda: store.add_note(conn, user["id"], str(player_id), body.body, season))

    @router.patch("/notes/{note_id}")
    def update_note(conn: Conn, user: User, note_id: UUID, body: NotePatch) -> dict:
        row = guarded(lambda: store.update_note(conn, user["id"], str(note_id), body.body))
        if row is None:
            raise _not_found("Note")
        return row

    @router.delete("/notes/{note_id}", status_code=204)
    def delete_note(conn: Conn, user: User, note_id: UUID) -> Response:
        if not store.delete_note(conn, user["id"], str(note_id)):
            raise _not_found("Note")
        return Response(status_code=204)

    return router
