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
| D019 | Player comparison: grouped bars, no radar, 95 % difference test on regressed estimates | Accepted |
| D020 | Scouting: threshold screening, Pareto tiers, maximin, near misses, no weighted score | Accepted |
| D021 | Team analysis: exact xPts, PPDA, style shares, within-league percentiles | Accepted |
| D022 | Player similarity: regressed z-scores, Euclidean distance chosen by fingerprint test | Accepted |
| D023 | Shot maps as zone aggregates, never individual shots through the API | Accepted |
| D024 | Self-hosted deployment: one code-only image, data bootstrapped on the host | Accepted |
| D025 | Expected Threat (xT) as a progression metric | Accepted |
| D026 | Player zone maps on a 6 × 5 channel grid; canonical left/right convention | Accepted |
| D027 | Pressing metrics and maps from provider-independent defensive events | Accepted |

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

---

### Decision D019 — Player comparison

Date: 2026-10-05

Status: Accepted

Context: Comparing 2–4 players invites "who is better?". Raw gaps between per-90 values ignore sample noise. Two players can differ by 20 % on a metric purely by chance.

Decision:
- Compare 2–4 player-seasons. Metrics come from the union of the players' position templates. Mixed position groups are allowed with a warning, because percentiles are then relative to different populations.
- Each count metric carries a posterior standard deviation (migration 0004). A difference is **clear** when |r_A − r_B| > 1.96 × √(sd_A² + sd_B²); otherwise it is **within noise**. With 3–4 players, only the leader is tested against the second. Ratios are not tested.
- Visualisation: grouped horizontal percentile bars, one categorical colour per player (validated slots 1–4), value printed on every bar, verdict naming the player who is clearly ahead. **No radar chart.**

Reason: The rule is validated on held-out data. Clear differences persist 88–94 % of the time for most metrics, against 56–67 % for differences within noise. Radar charts distort comparisons (area grows with the square of the values, and the shape depends on axis order).

Alternatives considered: radar/pizza charts (popular in football media, misleading); showing raw differences without a test (invites over-interpretation); pairwise tests between all players (6 verdicts per metric for 4 players, unreadable).

Consequences: The verdict reflects sampling noise only, not team context or role. Interception differences are less persistent (73 %), which is documented. Ratios have no difference test in v1.

---

### Decision D020 — Scouting without a weighted score

Date: 2026-10-05

Status: Accepted

Context: Scouting needs to filter and order candidates on several criteria. A weighted score would need weights the data cannot justify (CLAUDE.md: no arbitrary scoring systems).

Decision:
- **Screening**: 1–6 criteria "metric ≥ X-th percentile" within one position group (eligible players, complete seasons). A ratio without enough attempts fails its criterion. Context filters: competition, team possession range.
- **Ordering**: Pareto tiers (non-dominated sorting), then weakest criterion (maximin), then minutes.
- **Near misses**: players failing exactly one criterion by ≤ 5 points (adjustable) are listed separately.
- **Role presets**: 8 editable presets documented in FOOTBALL_ANALYTICS.md. They pre-fill criteria and carry no hidden logic.
- Selected candidates can be sent to the comparison view (D019).

Reason: Filters and dominance are transparent and weight-free, and every ordering decision can be explained in one sentence. The half-season validation showed that hard thresholds are brittle but the selections are sound: shortlisted players stay at the 70th–86th percentile later on. That justified near misses.

Alternatives considered: weighted composite score (arbitrary weights); screening on regressed estimates (tested, no gain); similarity search "players like X" (planned for Phase 9).

Consequences: Two tier-1 candidates are not ordered against each other by the method, and that choice is left to the scout. Shortlists must be presented as a starting point, which the UI states.

---

### Decision D021 — Team analysis

Date: 2026-10-05

Status: Accepted

Context: Phase 8 must say whether teams deserved their results and how they played, comparably across teams.

Decision:
- Team-season metrics from canonical events, as ratios of season totals: points, goal difference, npxG for/against/difference, **expected points**, possession, PPDA, long and progressive pass shares, crosses, counter-attack and set-piece npxG shares, npxG per shot for and against.
- **xPts are computed exactly** (Poisson-binomial convolution of every shot's xG), not by simulation. This is deterministic and testable.
- **Percentiles within each league-season**, not pooled. Validation showed league norms (e.g. PPDA, set-piece shares) differ enough that pooling mixes league and style.
- Snapshot tables `team_seasons` and `team_season_metrics` (migration 0005), API `/api/teams` and `/api/teams/{id}/seasons/{id}`, and a Teams page with a style map (possession × pressing) and a quality map (npxG for × against).
- Counter-attack and set-piece shares rely on StatsBomb possession origins and are capability-gated.

Reason: npxG difference and xPts predicted second-half points better than first-half points or goal difference (r 0.70 vs 0.62). Within-league percentiles remove a demonstrated league effect.

Alternatives considered: simulated xPts (non-deterministic); pooled percentiles (league bias); PPDA without fouls (deviates from the public definition, which would make results harder to compare with other sources).

Consequences: Teams from different leagues are compared on values, not percentiles. xPts ignore game state and treat rebound shots as independent.

---

### Decision D022 — Player similarity

Date: 2026-10-05

Status: Accepted

Context: "Find players like X" is a core recruitment tool. CLAUDE.md requires a documented methodology and forbids arbitrary similarity percentages.

Decision:
- Variables: the regressed per-90 count metrics of the target's position template. Population: eligible players of the same group (four leagues pooled). Normalisation: z-scores within the group.
- Distance: **Euclidean**, selected among four candidates by a fingerprint test (recognising the same player across two half-seasons).
- Displayed: similarity percentile ("closer than X % of the group") and the two largest per-metric differences. No "% similar" score.
- Endpoint `/api/players/{id}/seasons/{id}/similar`, and a "Players with a similar profile" section on the player page with a link to the comparison view.

Reason: The fingerprint test gives an objective selection criterion. Euclidean on regressed values ties for best, keeps volume information and is robust for low-minute targets. Mahalanobis was measurably worse.

Alternatives considered: cosine (tied, but ignores volume); Mahalanobis (worse, over-weights noise); hand-weighted metrics (unjustified); clustering into "player types" (labels would be arbitrary; possible future work).

Consequences: Results are a neighbourhood of comparable profiles (own profile in the top 10 % about 60 % of the time), not an exact match. Goalkeepers have too few template count metrics for a meaningful profile (2): their similarity rests on claims and sweeper actions only, a documented limitation.

---

### Decision D023 — Shot maps as zone aggregates

Date: 2026-10-05

Status: Accepted

Context: Shot maps are a standard football visual. Plotting every shot through the API would serve event-level provider data, which D004 forbids for public use.

Decision: Shots are aggregated into six zones defined by the pitch markings (six-yard box, central and wide penalty area) and a 25 m edge-of-box line. For each zone the view gives shots, goals, npxG, npxG per shot and share of shots, compared with the player's position group or the team's league. Endpoints `/api/players/{id}/seasons/{id}/shots` and `/api/teams/{id}/seasons/{id}/shots` return zone aggregates only (a test asserts that no coordinates are returned). The UI draws a half-pitch shaded by share of shots (single hue, opacity = magnitude) with a table equivalent.

Reason: Licence compliance, and robustness: zone shares and xG per shot are harder to over-read than about 80 individual dots. Validation confirmed the zones are consistent (monotonic xG per shot, exact conservation).

Alternatives considered: individual shot dots through the API (event-level data, D004); hexbin grids (finer, but sparse per player and harder to read); individual-shot static images (possible later for local publication with attribution).

Consequences: Within-zone detail (exact angle, distance) is not shown. Penalties are reported separately.

---

### Decision D024 — Self-hosted deployment

Date: 2026-10-05

Status: Accepted (hosting chosen by the developer: self-hosted Portainer)

Context: The portfolio needs a live demo. The full database is about 3.4 GB, and StatsBomb data must not be redistributed (D004), so it cannot be baked into a public image.

Decision:
- **One Docker image** containing code only: the FastAPI app also serves the built frontend (same origin, no extra web server), and the same image runs the data bootstrap. It is multi-arch (amd64 and arm64) and published to **Docker Hub** (`safsaf90/football-scouting-analytics`, the developer's registry) by CI after all tests pass, using repository secrets.
- **Bootstrap service** (`deploy/bootstrap.sh`): on first start it downloads StatsBomb Open Data on the host, loads PostgreSQL and computes both analytics snapshots, then deletes raw files. It is idempotent.
- **A fresh install pins the audited release** (commit `4b73468`), not the newest data, because the coverage review (D010) is only valid for that release.
- **Portainer stack** (`deploy/portainer-stack.yml`): PostgreSQL without a published port, the bootstrap, and the app. Operations guide: `deploy/README.md`.

Reason: Licence-compliant (data never leaves the host in raw form and is never stored in an image), reproducible (verified: a fresh stack install gives identical results), and simple: one image and three services.

Alternatives considered: shipping a database dump (redistribution); a slim demo database built elsewhere (still redistribution of event data); a separate Nginx container for the frontend (an extra service for no benefit).

Consequences: The first start takes about 15 minutes and needs about 4 GB RAM (measured peak 3.4 GB). Publishing needs the `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` repository secrets; without them CI skips publishing with a warning.

---

### Decision D025 — Expected Threat (xT) as a progression metric

Date: 2026-10-08

Status: Accepted

Context: Assists and key passes ignore actions before the final pass. Clubs value players who progress the ball into dangerous zones.

Decision: Implement Karun Singh's xT on a 16 × 12 grid, fitted by value iteration on open-play actions, with g(z) taken from mean StatsBomb xG. Value successful open-play passes and carries as xT(end) − xT(start). Add `xt_pass` and `xt_carry` (regressed) to player metrics and to the creation/progression themes of position templates, which also feeds similarity. A shared `pitch_grid` module is introduced for the zone maps that follow.

Reason: Public, explainable method. Validation shows xT is a stable player trait (r = 0.80 between half-seasons) and strongly tied to team chance creation (r = 0.91 with team npxG).

Alternatives considered: possession-value models with machine learning (VAEP, OBV-like): less transparent and need more data; penalising failed actions (v2 candidate).

Consequences: The pre-registered criterion (predicting a player's own npxG + xA) failed and is documented. xT is presented as a progression metric only. Failed actions are not penalised in v1.

---

### Decision D026 — Player zone maps

Date: 2026-10-08

Status: Accepted

Context: Scouts want to see where a player plays, receives and progresses the ball, not only how much.

Decision: Three zone maps (touches, receptions, progression) on a 6 × 5 grid whose channels follow the pitch markings (wings, half-spaces, centre). Receptions come from the pass recipient field (provider-independent), not from StatsBomb ball-receipt events. Each map is compared with the position group's pooled distribution, and the API returns aggregates only. A partial index on `events.pass_recipient_id` (migration 0006) keeps reception queries fast, and group baselines are cached per process.

The canonical convention is made explicit: **y = 68 is the attacking team's left**. The shot map drew it mirrored, a bug found by this feature's orientation check and fixed.

Reason: Channels are the vocabulary coaches use. Provider-independent definitions keep D001. Aggregates keep D004.

Alternatives considered: a uniform 16 × 12 grid (too sparse per player); continuous heatmaps by kernel density (look precise but smooth over the sample size and imply event-level detail); StatsBomb ball receipts (provider-specific).

Consequences: The first request for a position group takes about 4 s (baseline computation), and later ones are immediate.

---

### Decision D027 — Pressing metrics and maps

Date: 2026-10-08

Status: Accepted

Context: PPDA gives pressing intensity without a location. Scouts and analysts want to see where a team defends and wins the ball.

Decision: Two team metrics, defensive action height and final-third ball wins per match, plus two zone maps (defensive actions, ball wins) compared with the league average. They are built only from provider-independent events (tackles, interceptions, recoveries, fouls), and StatsBomb pressures are excluded. The zone-map renderer is now a shared component (`ZoneGrid`) for player and team maps.

Reason: Validated against PPDA in all four leagues (r −0.41 to −0.86). Comparable across providers.

Alternatives considered: StatsBomb pressure locations (richer, but provider-specific); defensive line height from tracking data (not available).

Consequences: The height metric compresses differences (40–48 m), so it is read through within-league percentiles.
