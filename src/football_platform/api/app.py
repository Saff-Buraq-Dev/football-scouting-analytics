"""HTTP API for player profiles (decision D018).

Serves derived, aggregated analytics only: no raw or event-level provider data (D004).

Run: .venv/bin/uvicorn football_platform.api.app:app --reload
Docs: http://127.0.0.1:8000/docs
"""

import os
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path
from typing import Annotated
from uuid import UUID

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from football_platform.analytics.definitions import ALL_METRICS, PositionGroup
from football_platform.analytics.scouting import DEFAULT_NEAR_MISS_POINTS
from football_platform.analytics.pitch_grid import Grid
from football_platform.analytics.similarity import similarity_features
from football_platform.analytics.xt import XTModel
from football_platform.api import repository
from football_platform.api.comparison import MAX_PLAYERS, MIN_PLAYERS, build_comparison
from football_platform.api.scouting import InvalidCriteriaError, build_scouting_result, parse_criteria, presets_payload
from football_platform.api.archetypes import overview as archetypes_overview
from football_platform.api.archetypes import player_view as archetype_player_view
from football_platform.api.corners import build_corner_report, season_corners
from football_platform.api.match import build_match_report
from football_platform.api.pressing import build_pressing_maps
from football_platform.api.pressing import counts as pressing_counts
from football_platform.api.profile import DATA_SOURCE, build_profile
from football_platform.api.shots import player_shot_map, team_shot_map
from football_platform.api.similarity import SimilarityUnavailableError, build_similarity
from football_platform.api.team import LABELS as TEAM_LABELS
from football_platform.api.team import build_team_profile, team_list_item
from football_platform.api.zones import build_zone_maps, map_counts
from football_platform.api.zones import frame as zone_frame
from football_platform.database.connection import database_url

# Vite dev server. A deployed frontend is served from the same origin.
DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
# In production (Docker image) the built frontend is served by this app, on the same origin.
FRONTEND_DIST_ENV = "FRONTEND_DIST"


def mount_frontend(app: FastAPI, dist: Path) -> None:
    """Serve the built single-page app: static assets, and index.html for every non-API route."""
    index = dist / "index.html"
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")
    if (dist / "attribution").is_dir():
        app.mount("/attribution", StaticFiles(directory=dist / "attribution"), name="attribution")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(index)


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

    @lru_cache(maxsize=16)
    def group_baseline(position_group: str) -> list[dict]:
        """Shots of a position group: the same for every request until the API restarts."""
        with psycopg.connect(db_url or database_url(), autocommit=True) as conn:
            return repository.group_shots(conn, position_group)

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

    @app.get("/api/players/{player_id}/seasons/{season_id}/similar")
    def similar_players(
        conn: Conn, player_id: UUID, season_id: UUID,
        limit: Annotated[int, Query(ge=1, le=50)] = 10,
    ) -> dict:
        row = repository.player_season(conn, str(player_id), str(season_id))
        if row is None:
            raise HTTPException(status_code=404, detail="No analytics for this player and season")
        if not row.get("position_group"):
            raise HTTPException(status_code=422, detail="Player has no position group")
        features = similarity_features(PositionGroup(row["position_group"]))
        rows = repository.similarity_population(conn, row["position_group"], features, str(player_id), str(season_id))
        try:
            return build_similarity(rows, features, f"{player_id}:{season_id}", limit)
        except SimilarityUnavailableError as error:
            raise HTTPException(status_code=422, detail=str(error)) from None

    @app.get("/api/players/{player_id}/seasons/{season_id}/shots")
    def player_shots(conn: Conn, player_id: UUID, season_id: UUID) -> dict:
        row = repository.player_season(conn, str(player_id), str(season_id))
        if row is None:
            raise HTTPException(status_code=404, detail="No analytics for this player and season")
        group = row.get("position_group")
        baseline = group_baseline(group) if group else []
        return player_shot_map(
            repository.player_shots(conn, str(player_id), str(season_id)), baseline,
            group or "none",  # position group key; the frontend words it
        )

    @lru_cache(maxsize=8)
    def group_zone_counts(position_group: str) -> dict:
        """Zone counts of a whole position group (baseline): computed once per group per process."""
        with psycopg.connect(db_url or database_url(), autocommit=True) as conn:
            return map_counts(zone_frame(repository.group_zone_events(conn, position_group)),
                              zone_frame(repository.group_passes_received(conn, position_group)))

    @app.get("/api/players/{player_id}/seasons/{season_id}/zones")
    def player_zones(conn: Conn, player_id: UUID, season_id: UUID) -> dict:
        row = repository.player_season(conn, str(player_id), str(season_id))
        if row is None:
            raise HTTPException(status_code=404, detail="No analytics for this player and season")
        group = row.get("position_group")
        baseline = group_zone_counts(group) if group else map_counts(zone_frame([]), zone_frame([]))
        return build_zone_maps(
            repository.player_zone_events(conn, str(player_id), str(season_id)),
            repository.passes_received(conn, str(player_id), str(season_id)),
            baseline, group,
        )

    @lru_cache(maxsize=8)
    def league_pressing_counts(season_id: str) -> dict:
        with psycopg.connect(db_url or database_url(), autocommit=True) as conn:
            return pressing_counts(repository.league_pressing_events(conn, season_id))

    @app.get("/api/teams/{team_id}/seasons/{season_id}/pressing")
    def team_pressing(conn: Conn, team_id: UUID, season_id: UUID) -> dict:
        if repository.team_season(conn, str(team_id), str(season_id)) is None:
            raise HTTPException(status_code=404, detail="No analytics for this team and season")
        return build_pressing_maps(repository.team_pressing_events(conn, str(team_id), str(season_id)),
                                   league_pressing_counts(str(season_id)))

    @lru_cache(maxsize=8)
    def league_corners(season_id: str):
        with psycopg.connect(db_url or database_url(), autocommit=True) as conn:
            return season_corners(repository.season_corner_events(conn, season_id))

    @app.get("/api/teams/{team_id}/seasons/{season_id}/corners")
    def team_corners(conn: Conn, team_id: UUID, season_id: UUID) -> dict:
        if repository.team_season(conn, str(team_id), str(season_id)) is None:
            raise HTTPException(status_code=404, detail="No analytics for this team and season")
        corners, pairs = league_corners(str(season_id))
        return build_corner_report(corners, pairs, str(team_id))

    @app.get("/api/teams/{team_id}/seasons/{season_id}/shots")
    def team_shots(conn: Conn, team_id: UUID, season_id: UUID) -> dict:
        if repository.team_season(conn, str(team_id), str(season_id)) is None:
            raise HTTPException(status_code=404, detail="No analytics for this team and season")
        shots_for, shots_against = repository.team_shots(conn, str(team_id), str(season_id))
        return team_shot_map(shots_for, shots_against, repository.league_shots(conn, str(season_id)))

    @app.get("/api/matches")
    def matches(conn: Conn, season_id: UUID | None = None, team_id: UUID | None = None) -> dict:
        rows = repository.matches_list(conn, str(season_id) if season_id else None, str(team_id) if team_id else None)
        return {"matches": rows, "data_source": DATA_SOURCE}

    @app.get("/api/matches/{match_id}")
    def match_report(conn: Conn, match_id: UUID) -> dict:
        match = repository.match_row(conn, str(match_id))
        if match is None:
            raise HTTPException(status_code=404, detail="Unknown match")
        stored = repository.latest_xt_values(conn)
        xt = (XTModel.from_values(Grid(stored["grid_columns"], stored["grid_rows"]), stored["cell_values"])
              if stored else None)
        return build_match_report(
            match, repository.match_events(conn, str(match_id)), repository.match_metrics(conn, str(match_id)),
            repository.match_appearances(conn, str(match_id)), repository.match_spells(conn, str(match_id)), xt,
        )

    @app.get("/api/archetypes")
    def archetype_overview(conn: Conn) -> dict:
        return archetypes_overview(repository.archetypes(conn))

    @app.get("/api/players/{player_id}/seasons/{season_id}/archetype")
    def player_archetype(conn: Conn, player_id: UUID, season_id: UUID) -> dict:
        view = archetype_player_view(repository.player_archetype(conn, str(player_id), str(season_id)),
                                     repository.archetypes(conn))
        if view is None:
            raise HTTPException(status_code=404, detail="No archetype for this player-season")
        return view

    @app.get("/api/scouting/presets")
    def scouting_presets() -> list[dict]:
        return presets_payload()

    @app.get("/api/scouting")
    def scouting(
        conn: Conn,
        position_group: PositionGroup,
        criterion: Annotated[list[str], Query(description="metric_key:min_percentile, 1 to 6 times")],
        season_id: UUID | None = None,
        min_possession: Annotated[float | None, Query(ge=0, le=100)] = None,
        max_possession: Annotated[float | None, Query(ge=0, le=100)] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        near_miss_points: Annotated[float, Query(ge=0, le=20)] = DEFAULT_NEAR_MISS_POINTS,
    ) -> dict:
        try:
            criteria = parse_criteria(criterion, position_group)
        except InvalidCriteriaError as error:
            raise HTTPException(status_code=422, detail=str(error)) from None
        rows = repository.scouting_population(
            conn, position_group.value, [c.metric_key for c in criteria],
            str(season_id) if season_id else None, min_possession, max_possession,
        )
        return build_scouting_result(rows, criteria, limit, near_miss_points)

    @app.get("/api/teams")
    def teams(conn: Conn, season_id: UUID | None = None) -> dict:
        sid = str(season_id) if season_id else None
        metrics = repository.team_season_metrics(conn, sid)
        items = [
            team_list_item(t, metrics.get((str(t["team_id"]), str(t["season_id"])), {}))
            for t in repository.team_seasons(conn, sid)
        ]
        return {"teams": items, "metric_labels": dict(TEAM_LABELS), "data_source": DATA_SOURCE}

    @app.get("/api/teams/{team_id}/seasons/{season_id}")
    def team_profile(conn: Conn, team_id: UUID, season_id: UUID) -> dict:
        team = repository.team_season(conn, str(team_id), str(season_id))
        if team is None:
            raise HTTPException(status_code=404, detail="No analytics for this team and season")
        metrics = repository.team_season_metrics(conn, str(season_id), str(team_id)).get(
            (str(team_id), str(season_id)), {})
        return build_team_profile(team, metrics, repository.team_squad(conn, str(team_id), str(season_id)))

    @app.get("/api/compare")
    def compare(
        conn: Conn,
        ps: Annotated[list[str], Query(description="player_id:season_id, 2 to 4 times")],
    ) -> dict:
        if not MIN_PLAYERS <= len(ps) <= MAX_PLAYERS:
            raise HTTPException(status_code=422, detail=f"Compare between {MIN_PLAYERS} and {MAX_PLAYERS} player-seasons")
        if len(set(ps)) != len(ps):
            raise HTTPException(status_code=422, detail="Each player-season can appear only once")
        rows, metrics = [], []
        for item in ps:
            try:
                player_id, season_id = (str(UUID(part)) for part in item.split(":"))
            except ValueError:
                raise HTTPException(status_code=422, detail=f"Invalid player-season {item!r}") from None
            row = repository.player_season(conn, player_id, season_id)
            if row is None:
                raise HTTPException(status_code=404, detail=f"No analytics for {item}")
            rows.append(row)
            metrics.append(repository.player_season_metrics(conn, player_id, season_id))
        return build_comparison(rows, metrics)

    dist = os.environ.get(FRONTEND_DIST_ENV)
    if dist and (Path(dist) / "index.html").is_file():
        mount_frontend(app, Path(dist))  # registered last: API routes take precedence
    return app


app = create_app()
