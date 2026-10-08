# Roadmap

## Phase 0 — Project foundation

Status: DONE

Objectives:

- establish project structure;
- define architecture principles;
- define agent responsibilities;
- define analytical methodology process.

Deliverables:

- CLAUDE.md
- PROJECT.md
- ROADMAP.md
- architecture documentation

---

## Phase 1A — Data-source strategy

Status: DONE (2026-10-04)

Objectives:

- evaluate open and commercial data providers;
- understand licensing per use context;
- design the provider-agnostic architecture and canonical model v1;
- select the initial dataset.

Deliverables:

- [docs/DATA_PROVIDERS.md](docs/DATA_PROVIDERS.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- decisions D001–D009 in [docs/DECISIONS.md](docs/DECISIONS.md)

---

## Phase 1B — Data discovery (StatsBomb Open Data)

Status: DONE (2026-10-04), except StatsBomb resource-centre registration (developer action)

Results: [docs/data/](docs/data/): coverage audit, data dictionary, mapping spec. Decisions D010–D012. Discovery scripts in `scripts/discovery/`.

Objectives:

- register at the StatsBomb resource centre (requested by the User Agreement);
- profile the StatsBomb open data locally (exploration only, no application code);
- audit coverage of each competition-season: complete vs partial (single team);
- confirm which 2015/16 men's leagues are complete;
- choose the analysis slice for Phases 2–4;
- verify open licence points marked *(verify)* in DATA_PROVIDERS.md: Wyscout public dataset (CC BY 4.0), IMPECT open-data licence, SkillCorner and PFF terms;
- validate the canonical model on paper against the Wyscout v2 and Opta event schemas.

Deliverables:

- data dictionary for the used StatsBomb entities;
- StatsBomb → canonical mapping specification (event types, positions, coordinates, outcomes);
- coverage audit table;
- canonical model v1.1 (adjusted after profiling);
- documented limitations.

Do not start application development before this phase is complete.

---

## Phase 2 — Canonical model and StatsBomb adapter

Status: DONE (2026-10-04)

Result: D011 slice ingested (1,517 matches, 5.3M events). All scores reconcile, and no team ever has more than 11 players. Decisions D013–D014. See [docs/data/STATSBOMB_MAPPING.md](docs/data/STATSBOMB_MAPPING.md) §6.

Objectives:

- implement the canonical model and ProviderCapabilities;
- implement the StatsBomb adapter (kloppy evaluated as an adapter-internal helper);
- reproducible download into a gitignored raw store;
- validate raw data and canonical output;
- enforce the layer dependency rule with a test.

Deliverables:

- canonical model code;
- StatsBomb adapter;
- ingestion pipeline;
- mapping and coordinate-conversion tests on synthetic fixtures;
- `.gitignore` entries for `data/`.

---

## Phase 3 — Database

Status: DONE (2026-10-04)

Result: PostgreSQL schema mirroring the canonical model (D015). The D011 slice is loaded: 1,517 matches and 5.3M events, with all constraints satisfied and scores reconciled in SQL.

Objectives:

- design relational model;
- create PostgreSQL schema;
- load cleaned data.

Deliverables:

- database schema;
- migrations;
- seed/import process.

---

## Phase 4 — Basic football analytics

Status: DONE (v1, 2026-10-04)

Result: player-season metrics (shooting, creation, progression, defending, aerials), per-90 values, position-group percentiles (D016). Validated on real data: goal conservation exact, known season totals reproduced. See [FOOTBALL_ANALYTICS.md](docs/FOOTBALL_ANALYTICS.md).

### Phase 4.1 — Methodological refinements

Status: DONE (2026-10-04)

Result: ratio minimums, goalkeeper metrics, regressed estimates with reliability (validated: −2 to −14 % prediction error), possession shown as context. A possession *adjustment* was tested and rejected (D017).

Objectives:

- calculate player statistics;
- calculate per-90 statistics;
- calculate percentiles where appropriate.

Deliverables:

- analytical modules;
- tests;
- methodology documentation.

---

## Phase 4B — Second provider adapter (optional)

Status: NOT STARTED

Objectives:

- implement a Wyscout public dataset (2017/18) adapter;
- run the same analytics unchanged on a second provider;
- document definitional differences between providers.

Purpose: prove provider-agnosticism with no licensing risk.

---

## Phase 5 — Player profiles

Status: DONE (2026-10-05)

Result: analytics snapshot in PostgreSQL, FastAPI (search + profile), React + TypeScript profile page with position templates, percentile meters, reliability and possession context (D018). Pending before public deployment: the official StatsBomb logo.

Objectives:

- create player pages;
- display statistics;
- display visualizations.

---

## Phase 6 — Player comparison

Status: DONE (2026-10-05)

Result: compare 2–4 players, with a validated "clear difference / within noise" verdict (D019).

Objectives:

- compare 2–4 players;
- normalize metrics;
- display meaningful visualizations.

---

## Phase 7 — Scouting

Status: DONE (2026-10-05)

Result: screening with role presets, Pareto tiers without a weighted score, near misses, possession context filter, shortlist stability validated (D020).

Objectives:

- filter players;
- define player profiles;
- rank candidates.

---

## Phase 8 — Team analysis

Status: DONE (2026-10-05)

Result: results vs underlying performance (exact xPts), playing-style metrics, style and quality maps, team profiles with squads. Predictive value and league effects validated (D021).

Objectives:

- analyze team performance;
- compare teams;
- identify team styles.

---

## Phase 9 — Advanced analytics

Progress: player similarity DONE (D022), shot zone maps DONE (D023), 2026-10-05.

Potential features:

- player similarity;
- clustering;
- shot maps;
- passing networks;
- pressing;
- tactical analysis.

Only implement features when the data supports them.

---

## Phase 9B — Commercial provider evaluation

Status: NOT STARTED

Objectives:

- revisit decision D003 with current market information;
- check licensing for public demonstration vs club-internal use;
- define the adapter work needed for the chosen provider.

No purchase without a concrete use case.

---

## Phase 11 — Feature expansion

Status: IN PROGRESS (started 2026-10-08)

Order chosen by dependencies. Each feature goes through analysis, tests, validation, documentation and a commit before the next starts.

1. ✅ Expected Threat (xT): value of every pass and carry; pitch grid shared with steps 2–3 (D025)
2. ✅ Pass and touch zone maps (player, zone aggregates) (D026)
3. ✅ Pressing maps (team, where the ball is won back) (D027)
4. ✅ Match pages (xG race, team comparison, standouts) (D028)
5. ✅ Passing networks (per team per match, on match pages) (D028)
6. ✅ Set-piece analysis (corner delivery zones and outcomes) (D029)
7. ✅ Player archetypes (clustering within position groups, stability-validated) (D030)
8. ✅ One-page scouting report (PDF) (D031)
9. Recruitment board (shortlists, tags, notes) behind an abstract authentication provider (development provider now, AWS Cognito later)

---

## Phase 10 — Portfolio / production

Progress (2026-10-05): StatsBomb logo attribution on every page, MIT license for the code, CI (backend with PostgreSQL + frontend), recruiter-oriented README with screenshots. Deployment-ready for self-hosted Portainer (D024): image published by CI, one-shot data bootstrap, stack file and guide (deploy/README.md). Fresh install verified end to end. Remaining: go live on the developer's server, write-up of findings.

Objectives:

- improve UX;
- improve performance;
- add documentation;
- deploy;
- create demonstrations;
- prepare portfolio presentation.