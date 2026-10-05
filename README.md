# Football Analytics Platform

A provider-agnostic football analytics and scouting platform, built as a professional portfolio project.

Football data from any provider is mapped into one **canonical model**. Analytics, API and frontend never depend on a specific provider. The first source is StatsBomb Open Data.

```text
Provider (StatsBomb open data) → Adapter → Canonical model → Analytics → API → Frontend
```

## Status

| Phase | State |
|---|---|
| 1A Data-source strategy | done: [docs/DATA_PROVIDERS.md](docs/DATA_PROVIDERS.md) |
| 1B Data discovery | done: [docs/data/](docs/data/) |
| 2 Canonical model + StatsBomb adapter | done: 1,517 matches of 2015/16 Premier League, La Liga, Serie A, Ligue 1 |
| 3 Database | done: PostgreSQL schema, migrations, transactional loader |
| 4 Basic football analytics | done: player-season metrics, per 90, percentiles, goalkeeping, regressed estimates (4.1) |
| 5 Player profiles | done: API + web interface (search, profile) |
| 6 Player comparison | done: 2–4 players, validated difference test |
| 7 Scouting | done: role presets, weight-free ranking (Pareto), near misses |
| 8 Team analysis | done: expected points, style metrics, style maps |
| 9 Advanced analytics | next |

See [ROADMAP.md](ROADMAP.md).

## Quick start

Requires Python 3.12.

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest                                   # tests (synthetic fixtures, no data needed)
.venv/bin/python -m football_platform.pipeline.ingest   # download + ingest (~5 min, ~4.3 GB raw, ~0.7 GB canonical)
```

Output: `data/canonical/statsbomb_open/<commit>/*.parquet` and a `manifest.json` with row counts, warnings and validation results.

Database (PostgreSQL 17 in Docker, localhost:5433):

```bash
cp .env.example .env
docker compose up -d
.venv/bin/python -m football_platform.pipeline.load_database   # applies migrations, loads (~5 min)
```

Database integration tests run automatically when the server is reachable. They use a temporary database.

Player-season report (metrics, per 90, percentiles):

```bash
.venv/bin/python -m football_platform.reports.player_season_report   # ~25 s -> data/analytics/
```

Web interface (two terminals):

```bash
.venv/bin/uvicorn football_platform.api.app:app --port 8000   # API, docs at /docs
cd frontend && npm install && npm run dev                      # http://localhost:5173
```

The report commands refresh the analytics snapshots the API reads:

```bash
.venv/bin/python -m football_platform.reports.player_season_report
.venv/bin/python -m football_platform.reports.team_season_report
```

## Data and licensing

**Data is not included in this repository.** The pipeline downloads StatsBomb Open Data, pinned to a specific commit, into the gitignored `data/` folder.

StatsBomb Open Data is provided under the [StatsBomb Public Data User Agreement](https://github.com/statsbomb/open-data): non-commercial use only, no redistribution, and published analysis must credit StatsBomb with its logo. See [docs/DATA_PROVIDERS.md](docs/DATA_PROVIDERS.md) and decision D004.

## Documentation

| Document | Content |
|---|---|
| [PROJECT.md](PROJECT.md) | objectives, scope |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | layers, adapter contract, canonical model |
| [docs/FOOTBALL_ANALYTICS.md](docs/FOOTBALL_ANALYTICS.md) | analytical methodology |
| [docs/DECISIONS.md](docs/DECISIONS.md) | decision log (D001–D021) |
| [docs/data/](docs/data/) | StatsBomb coverage audit, data dictionary, mapping specification |
