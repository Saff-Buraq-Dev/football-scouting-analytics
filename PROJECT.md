# Football Analytics Platform

## Objective

Build a professional-quality football analytics and scouting platform that shows real ability in football data engineering, data science and analysis. The intended audience is a professional football club.

The platform answers football questions such as:

- How productive is a player, adjusted for playing time?
- How does a player compare with peers in the same position and competition?
- Which players fit a defined scouting profile?
- How does a team play and perform?

## Scope

In scope (phased, see [ROADMAP.md](ROADMAP.md)):

- reproducible ingestion of event data through provider adapters;
- a provider-independent canonical data model;
- documented, tested player and team metrics (per-90, percentiles);
- player profiles, comparison, scouting filters, team analysis;
- a web interface built for analysts.

Out of scope for now:

- tracking data (Phase 9 at the earliest, decision D009);
- live/real-time data;
- cross-provider player matching;
- purchasing commercial data;
- any commercial use of the data.

---

## Data strategy

The platform must be designed to remain independent from any single football data provider.

The initial development environment should use a publicly available dataset such as StatsBomb Open Data.

However, the architecture must allow future integration with commercial football data providers such as:

- Hudl StatsBomb;
- Hudl Wyscout;
- Opta / Stats Perform;
- Sportradar;
- other providers where licensing permits.

The application should use an internal canonical data model.

External provider-specific schemas must be mapped into this canonical model through dedicated data-provider adapters.

The analytics layer must operate on the canonical model rather than directly on provider-specific data structures.

This allows the project to:

1. start with free data;
2. develop and test analytics;
3. switch or add data providers later;
4. preserve the same analytics and frontend;
5. compare data providers where appropriate.

Commercial datasets must only be used when their licensing terms explicitly permit the intended usage.

### Phase 1A outcome (2026-10-04)

| Topic | Decision |
|---|---|
| Initial dataset | **StatsBomb Open Data** (D002). Analysis slice chosen in Phase 1B. |
| Future commercial candidate | **Hudl StatsBomb**, with Opta and Wyscout as alternatives. No purchase now (D003). |
| Abstraction | Provider adapters → canonical model → analytics (D001). See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). |
| Provider evaluation | [docs/DATA_PROVIDERS.md](docs/DATA_PROVIDERS.md) |
| Initial analysis slice (Phase 1B) | Men's 2015/16 Premier League, La Liga, Serie A, Ligue 1. 1,517 matches; complete seasons, Ligue 1 has 377 of 380 (D011) |

### Licensing and use contexts

| Context | StatsBomb Open Data allowed? |
|---|---|
| Learning | Yes |
| Personal development | Yes |
| Portfolio / public demonstration | Yes, **with StatsBomb logo attribution** and **no redistribution of raw data** (D004) |
| Commercial use | **No** (User Agreement §1.2.2) |

Raw provider data is never committed to this repository. The code downloads it reproducibly.
