# Architecture and Analytical Decisions

This document records important decisions made during the project.

## Decision format

### Decision XXX

Date:

Status:

Context:

Decision:

Reason:

Alternatives considered:

Consequences:

---

## Index

| # | Title | Status |
|---|---|---|
| D001 | Provider-agnostic canonical data model | Accepted |
| D002 | StatsBomb Open Data as the initial data source | Accepted |
| D003 | Hudl StatsBomb as preferred future commercial candidate (no purchase) | Accepted |
| D004 | Raw provider data is never committed or redistributed | Accepted |
| D005 | Canonical pitch coordinate system | Accepted |
| D006 | Internal ids with external-id mapping | Accepted |
| D007 | Provider metrics are source-tagged and never substituted | Accepted |
| D008 | Scraped data sources are excluded | Accepted |
| D009 | Tracking data deferred to Phase 9 | Accepted |
| D010 | Season coverage classification gates population metrics | Accepted |
| D011 | Initial analysis slice: men's 2015/16 Premier League, La Liga, Serie A, Ligue 1 | Accepted |
| D012 | Canonical model v1.1 | Accepted |
| D013 | Phase 2 tooling: Python 3.12, dataclasses, no kloppy, Parquet | Accepted |
| D014 | Events override lineups for when a player leaves the pitch | Accepted |
| D015 | PostgreSQL schema = canonical model; plain SQL migrations; transactional reload | Accepted |
| D016 | Player-season metrics v1: definitions, 900-minute threshold, position-group percentiles | Accepted |
| D017 | Phase 4.1: ratio minimums, goalkeeper metrics, regressed estimates, no possession adjustment | Accepted |
| D018 | Player profiles: analytics snapshot in PostgreSQL, FastAPI, React + TypeScript | Accepted |

Evidence for D002, D003, D008 and D009 is in [DATA_PROVIDERS.md](DATA_PROVIDERS.md). Technical detail for D001 and D004–D007 is in [ARCHITECTURE.md](ARCHITECTURE.md).

---

### Decision D001 — Provider-agnostic canonical data model

Date: 2026-10-04

Status: Accepted

Context: The project starts with free data but must be able to use commercial feeds (Opta, Wyscout, Hudl StatsBomb) later. Each provider has its own schema, ids, coordinates and metric definitions.

Decision: All provider data is converted by a provider adapter into an internal canonical model. Analytics, API and frontend depend only on the canonical model. Adapters declare their `ProviderCapabilities`, and analytics checks them explicitly.

Reason: Swapping or adding providers then only means writing a new adapter. Analytics and its tests are reused unchanged.

Alternatives considered: (a) Use StatsBomb JSON directly everywhere: fastest start, but locks the project to one schema. (b) Use kloppy's data model as *the* canonical model: good tooling, but it couples us to a third-party library's model and lifecycle.

Consequences: An extra mapping layer to build and test. The canonical model v1 is kept deliberately minimal and validated on paper against StatsBomb, Wyscout v2 and Opta schemas. kloppy may still be used *inside* adapters.

---

### Decision D002 — StatsBomb Open Data as the initial data source

Date: 2026-10-04

Status: Accepted

Context: Phase 1 needs a free, legally usable event dataset rich enough for per-90 metrics, percentiles and shot analysis.

Decision: Use StatsBomb Open Data. The concrete analysis slice is chosen in Phase 1B after a coverage audit (see D011).

Reason: Richest free event specification (pressures, carries, related events), provider xG, 360 freeze frames for recent tournaments, mature tooling, same schema as a leading commercial product, and complete recent seasons for five women's leagues.

Alternatives considered: Wyscout public dataset (complete 2017/18 Big-5, CC BY 4.0, but no xG and a poorer event model). It is kept as a candidate second adapter. IMPECT open data (recent Bundesliga, packing; licence verified in Phase 1B as non-commercial, no redistribution). Aggregator APIs (current but no event coordinates).

Consequences: Licence restricts use to non-commercial analysis with logo attribution (see D004). Many seasons are partial, so coverage must be modelled. No player birth dates, so no age-based scouting with this source.

---

### Decision D003 — Hudl StatsBomb as preferred future commercial candidate

Date: 2026-10-04

Status: Accepted

Context: The platform should eventually be credible with current professional data.

Decision: Hudl StatsBomb is the first commercial candidate, with Opta / Stats Perform as the main alternative and Hudl Wyscout for scouting breadth. **Nothing is purchased now.**

Reason: Same schema family as the initial source (lowest migration cost) and the deepest event model. In practice, commercial data would most likely be provided by a club under its own licence rather than bought by an individual.

Alternatives considered: Opta (market standard, broadest coverage, strict enforcement); Wyscout (600+ competitions, common in clubs); Sportradar (live/betting focus, weaker analytical depth); Sportmonks (cheap, limited event detail).

Consequences: The canonical model must not be StatsBomb-shaped. That is why it is validated against Wyscout and Opta schemas. The decision is revisited before Phase 10 ("Commercial provider evaluation").

---

### Decision D004 — Raw provider data is never committed or redistributed

Date: 2026-10-04

Status: Accepted

Context: The StatsBomb Public Data User Agreement forbids distributing or providing the data to third parties (§1.2.1) and commercial exploitation (§1.2.2), and requires the StatsBomb logo on published analysis (§1.4). The repository and a future demo will be public.

Decision: `data/` is gitignored. The pipeline downloads data reproducibly from the source. Tests use small synthetic fixtures. Public outputs (demo, screenshots, write-ups) show derived/aggregated analysis only, with source attribution. No public endpoint serves raw or bulk event-level data.

Reason: Keeps the public portfolio within the licence while remaining fully reproducible for anyone who obtains the data themselves.

Alternatives considered: Committing a data subset for convenience. Rejected as redistribution.

Consequences: A deployed demo needs its own data download step and must be designed around aggregated outputs. Any doubt about a public feature is resolved conservatively or by asking the provider.

---

### Decision D005 — Canonical pitch coordinate system

Date: 2026-10-04

Status: Accepted

Context: Providers use different pitch systems (StatsBomb 120×80 with y downwards; Wyscout and Opta 0–100).

Decision: Canonical coordinates are metres on a standard 105×68 pitch, origin bottom-left, with the acting team attacking towards x = 105. Adapters convert.

Reason: Metres make distance-based definitions (e.g. progressive passes) readable and provider-independent.

Alternatives considered: Normalised 0–1 coordinates (provider-neutral but hides distance semantics); keeping StatsBomb units (provider coupling).

Consequences: Real pitch sizes are unknown, so distances are approximate. This is documented in FOOTBALL_ANALYTICS.md.

---

### Decision D006 — Internal ids with external-id mapping

Date: 2026-10-04

Status: Accepted

Context: Each provider has its own ids. The same player has different ids in different providers.

Decision: Canonical entities use internal ids. An `ExternalId(entity_type, internal_id, provider, provider_id)` mapping links them to providers.

Reason: Avoids leaking provider ids through the API and leaves room for future cross-provider matching.

Alternatives considered: Using provider ids directly (simple, but couples API and URLs to one provider).

Consequences: Cross-provider entity resolution is **out of scope** for now and is a documented risk.

---

### Decision D007 — Provider metrics are source-tagged and never substituted

Date: 2026-10-04

Status: Accepted

Context: xG, xA, OBV, packing etc. are proprietary models. StatsBomb xG and Opta xG for the same shot differ.

Decision: Provider metrics are stored with `source_provider` and `model_version`. The analytics layer never treats metrics from different providers as interchangeable and never silently replaces a missing metric with another provider's. Our own computed statistics are stored separately from provider-reported aggregates.

Reason: Football correctness. Comparing players on mixed xG models would be misleading.

Alternatives considered: A single generic `xg` column. Rejected because it hides the source.

Consequences: Comparisons across providers require an explicit, documented validation step.

---

### Decision D008 — Scraped data sources are excluded

Date: 2026-10-04

Status: Accepted

Context: Sites like FBref, Understat, WhoScored, Sofascore and FotMob are popular hobbyist sources. Opta terminated FBref's advanced data feed on 2026-01-20.

Decision: The project does not scrape or use data from these sites.

Reason: Their terms forbid scraping, the underlying data is licensed from commercial providers, and a portfolio aimed at clubs must show clean data governance.

Alternatives considered: None acceptable.

Consequences: Fewer free current-season statistics. Freshness is limited to what licensed open data provides.

---

### Decision D009 — Tracking data deferred to Phase 9

Date: 2026-10-04

Status: Accepted

Context: Open tracking data is tiny (Metrica 3 matches, SkillCorner ~10) or by request (PFF WC 2022). Commercial tracking is enterprise-only.

Decision: No tracking data until Phase 9. The canonical model leaves an optional freeze-frame link on events but no tracking entities.

Reason: Event data answers the core scouting questions for Phases 2–8. Tracking would add large complexity for little portfolio value at this stage.

Alternatives considered: Designing tracking entities now. Rejected as premature (CLAUDE.md "keep the architecture simple").

Consequences: Physical and off-ball analysis is unavailable until Phase 9.

---

### Decision D010 — Season coverage classification gates population metrics

Date: 2026-10-04

Status: Accepted

Context: The coverage audit ([data/STATSBOMB_COVERAGE.md](data/STATSBOMB_COVERAGE.md)) showed that most StatsBomb open-data club seasons contain only one team's matches (Barcelona, Leverkusen, PSG, Inter Miami, Arsenal).

Decision: Every season gets a reviewed `coverage_scope` (`complete` / `partial`) from the audit. Percentiles, rankings and league averages use `complete` seasons only. Partial seasons may be used for single-player or single-team analysis.

Reason: In a single-team season, opponents are observed only against one (usually dominant) team, so cross-player comparisons are biased.

Alternatives considered: Using all available matches as one pool. Rejected as statistically invalid.

Consequences: The audit script must be re-run whenever the pinned open-data commit changes. The classification is stored as data, not hard-coded in analytics.

---

### Decision D011 — Initial analysis slice

Date: 2026-10-04

Status: Accepted

Context: Phases 2–4 need one concrete, complete population. Options were complete men's 2015/16 leagues, complete women's 2023/24 leagues, both, or a single league.

Decision: Build Phases 2–4 on the **men's 2015/16 Premier League, La Liga, Serie A and Ligue 1** (1,517 matches). 1. Bundesliga 2015/16 is excluded from populations (Leverkusen-only). The women's 2023/24 leagues are the planned next extension.

Reason: Four complete leagues in the same season allow cross-league percentiles. Widely known players make results easy to sanity-check, which matters while the methodology is being validated. Men's recruitment is the main target audience.

Alternatives considered: Women's 2023/24 (recent, complete, differentiating; kept as the next extension). Both at once (doubles validation work). Premier League only (faster, but percentiles limited to one league).

Consequences: All analyses describe the 2015/16 season. The UI must make that explicit (it is historical, not current form). Ligue 1 has 3 missing matches, which must be documented wherever Ligue 1 totals are shown. Men's and women's populations must never be mixed when women's data is added.

---

### Decision D012 — Canonical model v1.1

Date: 2026-10-04

Status: Accepted

Context: Profiling StatsBomb data and validating the model on paper against Wyscout v2 and Opta ([data/STATSBOMB_MAPPING.md](data/STATSBOMB_MAPPING.md) §7) revealed gaps in v1.

Decision: Add event types `ball_receipt`, `dribbled_past`, `miscontrol`, `dispossessed`, `own_goal`. Represent duels with `duel_kind` (ground/aerial/loose_ball) plus an optional `aerial_won` attribute. Split `play_context` into action-level `set_piece` and possession-level `possession_origin`. Positions become `(line, role, side)`. New capabilities: `has_carries`, `has_ball_receipts`, `position_granularity`, `minutes_precision`.

Reason: Each change was required to represent at least one provider faithfully without inventing data. For example, StatsBomb records aerial wins as flags, and Wyscout v2 has only line-level positions.

Alternatives considered: Mirroring StatsBomb types one-to-one (provider coupling). Synthesising aerial-won duel events (creates events the provider did not record).

Consequences: Analytics must use capability checks for carries, receipts, pressures and position detail.

---

### Decision D013 — Phase 2 tooling

Date: 2026-10-04

Status: Accepted

Context: Phase 2 needed a runtime, a modelling approach, a parsing strategy and an output format before PostgreSQL exists (Phase 3).

Decision: Python 3.12 in a project `.venv` with `pyproject.toml` (pip, no extra tooling). Canonical model as frozen standard-library dataclasses with explicit validation. StatsBomb JSON is mapped directly, without kloppy. Canonical output is Parquet via pyarrow. The layer dependency rule is enforced by a test that parses imports.

Reason: Minimal dependencies (pyarrow, plus pytest for development). The explicit mapping is the part a reviewer should be able to read and test. Parquet stores 5.3M events compactly and loads easily into PostgreSQL.

Alternatives considered: pydantic (more validation features, extra dependency); kloppy (multi-provider loaders, but its own model would need re-mapping); JSON Lines output (several GB, slow); import-linter (extra tool for one rule).

Consequences: Validation logic is hand-written and must be tested. Re-evaluate pydantic when the API (Phase 5) needs schema serialisation.

---

### Decision D014 — Events override lineups for when a player leaves the pitch

Date: 2026-10-04

Status: Accepted

Context: The first Premier League 2015/16 ingestion failed the minutes validation for 91 of 760 team-matches. StatsBomb lineup spells sometimes continue after a red card or a substitution (through later "Tactical Shift" spells), and some spells overlap.

Decision: A player's playing time ends at their earliest substitution-off or dismissal **event**. Overlapping spells are trimmed. A starter is anyone on the pitch at 00:00 of period 1. Every correction is logged as a warning.

Reason: Minutes played is the denominator of every per-90 metric. Substitution and card events are directly observed and reconcile with the official scores, while the spell anomalies are internally inconsistent (e.g. a spell running backwards in time).

Alternatives considered: Trusting lineup spells (gave up to 141 extra team-minutes in a match); dropping inconsistent matches (loses data and biases samples).

Consequences: After the rule, all 1,517 matches pass the "never more than 11 players" check. Nine team-matches have shortfalls over 10 minutes, all explained by recorded "Player Off" events. Details in [data/STATSBOMB_MAPPING.md](data/STATSBOMB_MAPPING.md) §6.

---

### Decision D015 — Database design

Date: 2026-10-04

Status: Accepted

Context: Phase 3 needs persistent, queryable storage for the canonical model (5.3M events for the D011 slice), ready for the analytics of Phase 4.

Decision:
- PostgreSQL 17 in Docker Compose, bound to localhost (port 5433, because 5432 is used by another local project). Credentials in a gitignored `.env`.
- The schema mirrors the canonical model one-to-one: same tables, internal UUIDs, foreign keys, and TEXT + CHECK constraints for every enumeration. A test keeps the CHECK lists identical to `canonical/enums.py`. No metrics are stored: analytics stay in tested code.
- Plain SQL migrations (`database/migrations/NNNN_*.sql`) with a small runner that records a checksum per migration and refuses edits to applied ones.
- The loader (`pipeline/load_database.py`) runs in one transaction. It upserts reference entities, replaces the content of the loaded matches, and verifies database row counts against the Parquet files.
- Integration tests create and drop a temporary database. They are skipped when no server is reachable.

Reason: The canonical model is already validated and documented, and mirroring it avoids a second mapping. CHECK constraints catch canonical-vocabulary drift at load time. Plain SQL keeps the schema readable for a reviewer without an ORM.

Alternatives considered: Alembic + SQLAlchemy (more tooling than needed without an ORM); PostgreSQL ENUM types (harder to evolve); DuckDB on Parquet only (simpler, but the roadmap targets a server database for the API).

Consequences: A full reload of the D011 slice takes about 5 minutes, dominated by constraint checking on 5.3M events. That's acceptable for occasional reloads. If it becomes a bottleneck, indexes can be dropped and re-created around the load. Database size is about 2.2 GB.

---

### Decision D016 — Player-season metrics v1

Date: 2026-10-04

Status: Accepted (defaults open to review by the developer)

Context: Phase 4 introduces the first football metrics. Their definitions, sample-size rule and comparison populations determine what every later ranking means.

Decision:
- Metric definitions as documented in [FOOTBALL_ANALYTICS.md](FOOTBALL_ANALYTICS.md) ("Phase 4"): shooting (non-penalty), chance creation (key passes, assists, derived xA), progression (Wyscout-style progressive actions, final-third and box entries), defending, aerials.
- Unit: player × competition-season.
- Minimum **900 minutes** for per-90 values and percentiles (configurable).
- Percentiles within **position groups** derived from the role with the most minutes, pooled across the complete seasons of the D011 slice.
- Capability-gated metrics (xG, xA, carries, pressures) are NaN when the source lacks them. xG from several providers is refused (D007).
- Computation in pandas inside `analytics/`, which imports only `canonical`. The `reports/` layer reads PostgreSQL and calls analytics.

Reason: Conventional, explainable choices from public football analytics. Every rule has a written football rationale and a test.

Alternatives considered: SQL views for metrics (harder to test, mixes logic into the database layer, contradicts D015); a 1,000- or 1,350-minute threshold (more stable values, smaller populations); percentiles per league instead of pooled (smaller populations of ~20–40 per group).

Consequences: Defensive metrics are not possession-adjusted yet (documented caveat). Wing-backs are grouped with full-backs and wide midfielders with wingers. These groupings may be refined after review.

---

### Decision D017 — Phase 4.1 methodological refinements

Date: 2026-10-04

Status: Accepted (possession option chosen by the developer)

Context: The v1 validation (D016) found unstable ratios on few attempts, small-sample noise, defensive metrics confounded by possession, and no goalkeeper metrics.

Decision:
1. **Ratios** are ranked only above a minimum denominator (100 passes, 30 aerial duels, 20 shots, 40 shots on target faced), derived from the binomial standard error. Values remain visible with a `_reliable` flag.
2. **Goalkeeper metrics**: opponent shots are attributed to the keeper on the pitch (position spells). Non-penalty save %, claims, sweeper actions, long-pass share. Reported for the goalkeeper group only. PSxG / goals prevented: unavailable in open data.
3. **Regressed estimates** (empirical Bayes towards the position-group mean) with a reliability weight. Percentiles still describe observed values.
4. **No possession adjustment.** The PAdj sigmoid was implemented, measured and rejected: it turns a −0.22 correlation into +0.87. Calibrated alternatives were unstable on held-out leagues. Defensive values stay raw, with `team_possession_pct` as context.

Reason: Every refinement was validated on the data. Regressed estimates cut second-half prediction error by 2–14 %, and goal accounting is exact. The one refinement that failed validation was not shipped.

Alternatives considered: PAdj sigmoid (over-corrects); data-calibrated elasticity per action (unstable out of sample); linear per-opportunity normalisation (implies an even stronger elasticity of 1).

Consequences: Defensive rankings partly reflect team style. The UI must show team possession next to them. Revisit possession adjustment with multiple seasons.

---

### Decision D018 — Player profiles: snapshot, API and frontend

Date: 2026-10-05

Status: Accepted

Context: Phase 5 exposes player-season profiles to scouts. Recomputing analytics from 5.3M events per request (~25 s) is not viable, and the API must never redistribute raw provider data (D004).

Decision:
- **Analytics snapshot.** `reports.player_season_report` stores its results in `player_seasons` and `player_season_metrics` (migration 0002), replacing the previous snapshot in one transaction. `analytics_runs` records each run (threshold, population, provider). The computation stays in tested Python code; the tables only hold its output. This refines D015 ("no metrics stored"): metrics are *computed* in code and *cached* in the database.
- **API**: FastAPI in a new `api/` layer (imports canonical, analytics, database). Read-only endpoints: health, seasons, metric definitions, player search (accent-insensitive via `unaccent`, migration 0003), player-season profile. **No endpoint serves events or raw provider data** (tested).
- **Profile assembly** is pure Python (`api/profile.py`): position templates (`analytics/profile_templates.py`), reliability bands, reasons for missing percentiles.
- **Frontend**: React + TypeScript + Vite in `frontend/`. No UI framework: a small token-based stylesheet with light and dark themes. Percentiles are drawn as meters in a single validated hue (a percentile is descriptive, so there is no good/bad colour), with a median marker, tooltips on hover and keyboard focus, and a full table as the accessible equivalent.

Reason: The database read path makes profiles instant. FastAPI keeps one language for backend and analytics. React + TypeScript is the expected standard for a professional frontend, and plain CSS tokens keep the design system explicit and small.

Alternatives considered: computing on request (too slow); a materialised SQL view (moves logic into SQL); server-rendered templates or HTMX (simpler, but less suited to the interactive comparison and scouting views of Phases 6–7); a UI framework such as Tailwind or MUI (faster start, weaker design identity).

Consequences: The snapshot must be refreshed (`player_season_report`) after each ingestion or methodology change. Before any public deployment, the official StatsBomb logo must be added to the UI (User Agreement §1.4).
