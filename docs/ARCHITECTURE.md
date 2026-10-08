# Architecture

Status: **v1.1 (Phase 1B, 2026-10-04)**. Design only. Nothing here is implemented yet.

v1.1 changes come from profiling StatsBomb data and validating against Wyscout v2 and Opta on paper. See [data/STATSBOMB_MAPPING.md](data/STATSBOMB_MAPPING.md) §7.

Related documents: [DATA_PROVIDERS.md](DATA_PROVIDERS.md) (why these providers), [DECISIONS.md](DECISIONS.md) (D001–D009), [FOOTBALL_ANALYTICS.md](FOOTBALL_ANALYTICS.md) (metric definitions).

---

## 1. Goals

1. Start with free data (StatsBomb Open Data) and later add commercial providers **without changing the analytics, API or frontend**.
2. Keep every football number traceable to its source (provider, file, ingestion run).
3. Respect licensing by design: raw provider data never leaves the developer's machine/server in raw form.
4. Stay a **modular monolith**: one Python codebase, clear package boundaries, no microservices.

---

## 2. Layers

```text
┌──────────────────────────────────────────────────────────────┐
│ External provider (StatsBomb open data, later Opta/Wyscout…) │
└──────────────────────────────┬───────────────────────────────┘
                               ↓  download (reproducible, versioned)
┌──────────────────────────────────────────────────────────────┐
│ RAW store: immutable provider files, gitignored              │
│ data/raw/<provider>/<release>/…  (never redistributed, D004) │
└──────────────────────────────┬───────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────┐
│ PROVIDER ADAPTER  providers/<name>/                          │
│  parse → validate provider schema → map to canonical         │
│  convert coordinates, map ids, map event types               │
│  declare ProviderCapabilities                                │
└──────────────────────────────┬───────────────────────────────┘
                               ↓  only canonical objects cross this line
┌──────────────────────────────────────────────────────────────┐
│ CANONICAL MODEL  canonical/                                  │
│  Competition, Season, Team, Player, Match, Appearance, Event │
│  validated, provider-independent, with provenance            │
└──────────────────────────────┬───────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────┐
│ ANALYTICS  analytics/                                        │
│  minutes, player/team match stats, per-90, percentiles…      │
│  reads canonical only; checks capabilities explicitly        │
└──────────────────────────────┬───────────────────────────────┘
                               ↓
               API (api/)  →  Frontend (frontend/)
```

### Dependency rule

Imports may only point **downwards** in this order: `api → analytics → canonical`, `providers → canonical`. Also `reports → analytics, database`, `pipeline → providers, database`, `api → analytics, database, auth, board`, `board → database`, `auth → (nothing)`, and `database → canonical`. The full table is enforced in `tests/test_architecture.py`.

- `analytics`, `api` and `frontend` must **never** import from `providers/`.
- `canonical` imports nothing from the project except itself.
- Only the pipeline/orchestration code knows which adapter to call.

This rule will be enforced by an automated test (import-linter or an equivalent check) once code exists.

---

## 3. Provider adapter contract (conceptual)

Each provider is implemented as one adapter that offers the same operations:

| Operation | Returns |
|---|---|
| `capabilities()` | `ProviderCapabilities` (below) |
| `list_competitions()` | canonical `Competition` + `Season` records |
| `list_matches(season)` | canonical `Match` records |
| `get_appearances(match)` | canonical `Appearance` (lineup) records |
| `get_events(match)` | canonical `Event` records |
| `get_freeze_frames(match)` *(optional)* | canonical freeze-frame records, only if capability declared |

Adapters are responsible for:

- reading **only** from the raw store (no network calls during transformation);
- validating the provider schema and failing loudly on unexpected shapes;
- **never silently discarding data**: unmapped events are kept with `type = other` and logged;
- coordinate conversion, id mapping, event-type mapping, position mapping.

### ProviderCapabilities

A declared, static description of what a provider can deliver. The analytics layer checks it instead of assuming:

| Capability | StatsBomb open | Wyscout public (v2) | Opta (typical) |
|---|---|---|---|
| `source_coordinate_system` | 120×80, attack →| 0–100, y inverted | 0–100 |
| `has_event_end_locations` | yes | yes (passes/shots) | yes (via qualifiers) |
| `has_provider_xg` | yes | no | yes (contract-dependent) |
| `has_pressure_events` | yes | no | no (different concept) |
| `has_carries` | yes | no | no |
| `has_ball_receipts` | yes | no | no |
| `has_freeze_frames` | some seasons (360) | no | no |
| `has_possession_ids` | yes | no | derivable |
| `has_player_birth_date` | **no** | yes | yes |
| `has_position_spells` | yes | no (role only) | yes |
| `position_granularity` | `slot` | `line` | `slot` |
| `minutes_precision` | `second` | `minute` | `second` |

Example: a "pressures per 90" metric is computed only for sources where `has_pressure_events` is true. Elsewhere it is reported as *unavailable*, never as zero.

---

## 4. Cross-cutting design rules

### 4.1 Identity (D006)

- Every canonical entity has an **internal id** owned by the platform.
- An `ExternalId` mapping records `(entity_type, internal_id, provider, provider_id)`.
- With a single provider, the mapping is 1:1. **Cross-provider entity resolution** (knowing that StatsBomb player 5503 and Wyscout player 3359 are the same person) is **out of scope** and a documented risk. It requires a matching method (name + DOB + team + dates) of its own.

### 4.2 Coordinates (D005)

- Canonical pitch: **105 × 68 metres**, origin at the bottom-left corner, **x = 0 at the acting team's own goal line, attacking towards x = 105**. Facing the opponent's goal, **y = 68 is the attacking team's left touchline** and y = 0 its right. Drawings must respect this, otherwise left and right are mirrored (a bug found and fixed in the shot map, Phase 11.2).
- Adapters convert. StatsBomb: `x_m = x / 120 × 105`, `y_m = (80 − y) / 80 × 68` (StatsBomb's y grows downwards). Wyscout/Opta: `x_m = x / 100 × 105`, with the y flip chosen per provider. Exact formulas are verified by tests in Phase 2.
- **Limitation:** real pitch dimensions vary (100–110 m × 64–75 m) and are rarely supplied. Distances in metres are therefore approximations, which matters for metrics like "progressive pass ≥ 10 m".

### 4.3 Event taxonomy

A small canonical set, informed by SPADL (socceraction) and kloppy:

`pass, shot, own_goal, carry*, ball_receipt*, pressure*, take_on, dribbled_past, duel, interception, clearance, block, ball_recovery, miscontrol, dispossessed, foul_committed, foul_won, goalkeeper_action, card, substitution, period_start, period_end, other`

\* capability-gated: exists only where the provider records it.

`duel` has a `duel_kind` (`ground`, `aerial`, `loose_ball`). Tackles are ground duels. Because StatsBomb records aerial *wins* as a flag on the winner's action, every event has an optional `aerial_won` attribute. The full StatsBomb mapping is in [data/STATSBOMB_MAPPING.md](data/STATSBOMB_MAPPING.md).

Each canonical event keeps `provider_event_type` and `provider_qualifiers` for traceability. Definitions differ between providers (what counts as a "dribble", a "duel", a "key pass"). Mapping decisions are documented per adapter in Phase 1B/2.

### 4.4 Provider metrics (D007)

Provider-computed values (StatsBomb xG, OBV, Wyscout xA, IMPECT packing) are stored as **source-tagged values**: `(metric_key, value, source_provider, model_version)`. They are never renamed into a generic `xg` that hides their origin, and one provider's value is never substituted for another's.

### 4.5 Provenance

Every canonical record carries: `source_provider`, `source_record_id`, `source_release` (e.g. git commit of the open-data repo), `ingestion_run_id`.

### 4.6 Coverage metadata

`Season.coverage` states whether a season is **complete** or **partial** (e.g. "Barcelona matches only"). Population-based analytics (percentiles, rankings) **must refuse** partial-coverage seasons, or show them with an explicit warning (see [FOOTBALL_ANALYTICS.md](FOOTBALL_ANALYTICS.md)).

### 4.7 Licensing by design (D004)

- `data/raw/` and any derived event-level files are gitignored.
- The pipeline downloads data reproducibly from the source. The repository contains **code, not data**.
- A public demo exposes **aggregated / derived** outputs only and shows source attribution (StatsBomb logo). No public endpoint returns raw or event-level provider data in bulk.

---

## 5. Canonical model v1

Legend: **R** = required, provider-independent. **O** = optional (absent for some providers).

### Competition
| Field | R/O | Notes |
|---|---|---|
| id | R | internal |
| name | R | |
| area | R | country or region (e.g. "Europe", "International") |
| gender | R | `male` / `female` |
| competition_type | R | `league` / `cup` / `international_tournament` |
| is_youth | O | |
| tier | O | league level, if known |

### Season
| Field | R/O | Notes |
|---|---|---|
| id, competition_id | R | |
| label | R | "2023/2024" or "2024" |
| start_date, end_date | O | often derivable from matches |
| coverage_scope | R | `complete` / `partial` |
| coverage_note | O | e.g. "matches involving Barcelona only" |
| has_events, has_lineups, has_freeze_frames | R | booleans |

### Team
| Field | R/O | Notes |
|---|---|---|
| id, name | R | |
| team_type | R | `club` / `national` |
| gender | R | |
| area | O | |
| short_name | O | |

### Player
| Field | R/O | Notes |
|---|---|---|
| id, name | R | full name |
| known_name | O | e.g. nickname (StatsBomb `player_nickname`) |
| nationality | O | |
| birth_date | O | **not in StatsBomb open data**, so age analysis is unavailable |
| height_cm, preferred_foot | O | |

### Match
| Field | R/O | Notes |
|---|---|---|
| id, season_id | R | |
| match_date | R | |
| kickoff_time | O | local time as given by the source; time zone not guaranteed |
| home_team_id, away_team_id | R | |
| home_score, away_score | R | after extra time if played |
| went_to_extra_time, home_penalties, away_penalties | O | |
| stage / matchweek | O | |
| venue, referee | O | |
| status | R | `played` / `scheduled` / … |

### Appearance (lineup)
| Field | R/O | Notes |
|---|---|---|
| match_id, team_id, player_id | R | |
| shirt_number | O | |
| is_starter | R | |
| position_spells | R | list of `(position, period, start_s, end_s)`. `position = (line, role, side)`: line GK/DEF/MID/FWD; role GK, CB, FB, WB, DM, CM, WM, AM, W, CF; side L/C/R. Providers with `position_granularity = line` fill only `line` |
| minutes_played | R | **derived** by a documented method (period lengths incl. stoppage, subs, red cards). See FOOTBALL_ANALYTICS.md |

### Event
| Field | R/O | Notes |
|---|---|---|
| id, match_id | R | |
| period | R | 1, 2, 3, 4 (ET), 5 (shootout) |
| time_s | R | seconds since period start |
| team_id | R | |
| player_id | O | absent for some events (e.g. period markers) |
| type | R | canonical taxonomy (§4.3) |
| outcome | R | `success` / `fail` / `unknown` / `not_applicable` |
| start_x, start_y | O | canonical metres (§4.2) |
| end_x, end_y | O | |
| body_part | O | `foot_left`, `foot_right`, `head`, `other` |
| set_piece | O | the action itself restarts play: `corner`, `free_kick`, `throw_in`, `penalty`, `goal_kick`, `kick_off`; null = open play |
| possession_origin | O | how the possession began (StatsBomb `play_pattern`) |
| duel_kind | O | for `duel`: `ground` / `aerial` / `loose_ball` |
| aerial_won | O | true when the action won an aerial duel |
| related_event_ids | O | |
| possession_id | O | provider-derived sequence |
| under_pressure | O | StatsBomb-specific |
| provider_metrics | O | source-tagged values, e.g. StatsBomb xG (§4.4) |
| freeze_frame_ref | O | link to 360 data |
| provider_event_type, provider_qualifiers | O | raw type/qualifiers for traceability |
| provenance | R | §4.5 |

Type-specific attributes (e.g. pass `is_cross`, `is_through_ball`, `assisted_shot_id`; shot `is_goal`) live in typed sub-structures, defined in Phase 1B from the StatsBomb mapping spec.

### PlayerMatchStatistics
| Field | R/O | Notes |
|---|---|---|
| match_id, player_id, team_id | R | |
| minutes_played | R | from Appearance |
| core counts | R | shots, goals, passes attempted/completed, … **computed by the analytics layer from canonical events** |
| capability-gated metrics | O | e.g. pressures (only if source has them) |

Provider-reported aggregates (e.g. a provider's own "key passes") go in a **separate source-tagged table**. They are never mixed with our computed values.

### TeamMatchStatistics
Same pattern at team level (shots, goals, passes, field tilt…), plus possession share computed by a documented method. Provider-reported values are kept separately.

---

## 6. Module layout

```text
src/football_platform/
  canonical/        # dataclasses/pydantic models, enums, validation
  providers/
    base.py         # adapter interface + ProviderCapabilities
    statsbomb/      # StatsBomb open-data adapter (kloppy may be used *inside* only)
  database/         # connection + SQL migrations (PostgreSQL)
  pipeline/         # download, run adapters, validate, write Parquet, load database
  analytics/        # Phase 4: player-match counts, player-season per 90, percentiles (pandas)
  reports/          # Phase 4: database -> analytics -> report files + analytics snapshot (D018)
  api/              # Phase 5-8: FastAPI, aggregated data only (players, comparison, scouting, teams, matches)
  auth/             # Phase 11.9: identity providers behind one interface (disabled, dev, OIDC/Cognito), D032
  board/            # Phase 11.9: recruitment board (shortlists, tags, notes): user data, owner-scoped SQL
frontend/           # Phase 5: React + TypeScript (Vite); built into the Docker image and served by the API
deploy/             # Phase 10: Portainer stack, bootstrap script, deployment guide (D024)
scripts/
  discovery/        # Phase 1B exploration scripts (stdlib only, not application code)
tests/
  providers/statsbomb/   # fixture-based mapping tests (small, synthetic fixtures)
  canonical/
  analytics/
data/                    # gitignored
  raw/  canonical/
```

Tests use **small hand-written fixtures**, not copies of provider files, so the repository stays free of redistributed data.

Implemented in Phase 2: `canonical/`, `providers/base.py`, `providers/statsbomb/`, `pipeline/` (`download_statsbomb`, `validation`, `storage`, `ingest`).

### Canonical output (Phase 2)

`python -m football_platform.pipeline.ingest` writes one Parquet file per table to `data/canonical/statsbomb_open/<commit[:12]>/`:
`competitions, seasons, teams, players, matches, appearances, position_spells, events, provider_metrics, external_ids`, plus `manifest.json` (run id, source commit, row counts, warnings, validation issues).

### Database (Phase 3, decision D015)

PostgreSQL 17 (`docker compose up -d`, localhost:5433). The schema in `src/football_platform/database/migrations/0001_canonical_schema.sql` mirrors the canonical tables, with foreign keys and CHECK constraints for every canonical enumeration, plus an `ingestion_runs` table holding each run's manifest.

```bash
python -m football_platform.database.migrate          # apply pending migrations
python -m football_platform.pipeline.load_database     # load latest canonical output
```

Layer rule: `database/` (connection, migrations) may import only `canonical`. The loader lives in `pipeline/`.

### User data and login (Phase 11.9, decision D032)

The recruitment board is the only **user-generated** data and the only part of the API that writes. It is kept apart from football data:

```text
Browser ──(1) login: authorization code + PKCE──► Identity provider (Amazon Cognito, any OIDC)
   │  ◄────────────── access token (JWT, RS256) ──────────┘
   └─(2) Authorization: Bearer <token> ──► api/board.py ──► auth/ AuthProvider.authenticate() → Identity(issuer, subject)
                                                   └──► board/store.py (every query filtered by owner) ──► PostgreSQL
```

- **`auth/`**: one `AuthProvider` interface with three implementations chosen by `AUTH_PROVIDER`: `disabled` (default: board off, analytics stay public), `dev` (one local user, no credentials: local or private single-user instances only) and `oidc` (verifies RS256 JWTs: issuer, expiry, client via `aud` or Cognito's `client_id`, signature against the issuer's JWKS found through OpenID discovery). The API never sees a password. Switching to another provider means another implementation of the interface, nothing else.
- **`board/`**: SQL for shortlists, entries, tags and notes. Every query carries the owner id; another user's rows answer 404, like rows that do not exist.
- **Users** are created on first authenticated request, keyed by `(issuer, subject)`. Email and name are copied from the token when present.
- **Tables** (migration 0009): `app_users`, `shortlists`, `shortlist_entries` (player-season), `player_tags`, `player_notes`. They reference `players` and `seasons`, which reloads upsert and never delete, so analytics reruns never touch user data.
- **Frontend**: `auth/client.ts` exposes the same three modes. In `oidc` mode the browser runs the authorization-code flow with PKCE as a public client (no secret in the browser) and keeps the token in `sessionStorage`. The server provides the endpoints at `/api/auth/config`.

---

## 7. Known risks

| Risk | Impact | Mitigation |
|---|---|---|
| Licence breach via public repo/demo | Loss of data access, legal exposure | D004: no raw data in git, derived outputs only, attribution |
| Partial-coverage seasons used as populations | Misleading percentiles | `coverage_scope` + analytics refusal |
| No current men's club data for free | Portfolio analyses historical seasons | State the season clearly in the UI; design for commercial feeds |
| Metric definitions differ between providers | Silent comparability errors | Source-tagged metrics (D007), capability checks |
| Missing scouting attributes (DOB, contract, value) | Limited recruitment features | Document; `birth_date` optional; Wyscout public has DOB |
| Cross-provider identity | Duplicate players across sources | Out of scope; ExternalId design leaves room |
| Over-engineered canonical model | Wasted effort | v1 minimal; validated against StatsBomb, Wyscout v2 and Opta schemas |
| Provider withdraws access (FBref precedent) | Data loss | Adapter boundary; local immutable raw copy for private use |
