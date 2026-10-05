"""HTTP API for player profiles (decision D018).

Serves derived, aggregated analytics only: no raw or event-level provider data (D004).

Run: .venv/bin/uvicorn football_platform.api.app:app --reload
Docs: http://127.0.0.1:8000/docs
"""

from collections.abc import Iterator
from typing import Annotated
from uuid import UUID

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from football_platform.analytics.definitions import ALL_METRICS, PositionGroup
from football_platform.api import repository
from football_platform.api.profile import DATA_SOURCE, build_profile
from football_platform.database.connection import database_url

# Vite dev server. A deployed frontend is served from the same origin.
DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def create_app(db_url: str | None = None) -> FastAPI:
    app = FastAPI(
        title="Football Scouting Analytics API",
        description="Player-season profiles built on StatsBomb Open Data. Derived metrics only.",
        version="0.1.0",
    )
    app.add_middleware(CORSMiddleware, allow_origins=DEV_ORIGINS, allow_methods=["GET"], allow_headers=["*"])

    def connection() -> Iterator[psycopg.Connection]:
        with psycopg.connect(db_url or database_url(), autocommit=True) as conn:
            yield conn

    Conn = Annotated[psycopg.Connection, Depends(connection)]

    @app.get("/api/health")
    def health(conn: Conn) -> dict:
        run = repository.latest_run(conn)
        return {"status": "ok" if run else "no_analytics_snapshot", "analytics_run": run}

    @app.get("/api/seasons")
    def seasons(conn: Conn) -> list[dict]:
        return repository.seasons(conn)

    @app.get("/api/metrics")
    def metrics() -> list[dict]:
        return [
            {"key": m.key, "label": m.label, "kind": m.kind.value, "capability": m.capability,
             "min_denominator": m.min_denominator or None,
             "position_groups": sorted(m.position_groups) if m.position_groups else None}
            for m in ALL_METRICS
        ]

    @app.get("/api/players")
    def search_players(
        conn: Conn,
        q: Annotated[str | None, Query(min_length=2, max_length=60)] = None,
        season_id: UUID | None = None,
        position_group: PositionGroup | None = None,
        eligible_only: bool = False,
        limit: Annotated[int, Query(ge=1, le=repository.SEARCH_LIMIT_MAX)] = 25,
    ) -> dict:
        results = repository.search_players(
            conn, q, str(season_id) if season_id else None,
            position_group.value if position_group else None, eligible_only, limit,
        )
        return {"results": results, "data_source": DATA_SOURCE}

    @app.get("/api/players/{player_id}/seasons/{season_id}")
    def player_profile(conn: Conn, player_id: UUID, season_id: UUID) -> dict:
        row = repository.player_season(conn, str(player_id), str(season_id))
        if row is None:
            raise HTTPException(status_code=404, detail="No analytics for this player and season")
        metrics = repository.player_season_metrics(conn, str(player_id), str(season_id))
        return build_profile(row, metrics, float(row["min_minutes"]))

    return app


app = create_app()
