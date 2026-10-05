# Football Analytics Platform

## Project role

You are working on a professional-quality football analytics platform.

The goal is to build a portfolio project that demonstrates real football analytics, data science, software engineering and scouting capabilities.

The eventual objective is to create a project that could be presented to a professional football club as evidence of the developer's ability to work with football data.

---

## Developer profile

The developer has strong general IT and infrastructure experience.

They are comfortable with:

- Linux
- Docker
- APIs
- databases
- cloud infrastructure
- Python development
- networking
- software architecture

However, they are still learning:

- football analytics
- football data science
- statistical modelling
- scouting methodologies

Therefore, explanations are important.

Do not assume that the developer already understands football analytics concepts.

---

## Core principles

### 1. Football correctness comes before visual polish

A beautiful dashboard with meaningless football metrics is considered a failure.

Every important metric must have a clear football interpretation.

Before implementing an analytical feature, explain:

- what question it answers;
- why the metric is useful;
- how it is calculated;
- what its limitations are.

### 2. Do not invent data

Never fabricate football statistics.

If a required metric cannot be calculated from the available dataset, explicitly say so.

### 3. Do not invent methodologies

Do not create arbitrary scoring systems or similarity percentages.

Any ranking, score or similarity model must have a documented methodology.

### 4. Prefer reproducibility

All data transformations and analytical calculations should be reproducible.

Avoid manual spreadsheet calculations whenever possible.

### 5. Keep the architecture simple

Do not introduce unnecessary microservices, frameworks or infrastructure.

Prefer a modular monolith unless there is a clear reason for additional services.

### 6. Separate concerns

Keep these concepts separate:

- raw data
- cleaned data
- analytical transformations
- database models
- API
- frontend
- visualization
- business/football logic

### 7. Explain before implementing major changes

Before implementing a significant feature:

1. explain the problem;
2. explain the proposed solution;
3. identify assumptions;
4. identify limitations;
5. then implement it.

### 8. Test analytical calculations

Football statistics are part of the application's core business logic.

Important calculations must have automated tests.

### 9. Think like a professional analyst

Whenever possible, ask:

> "What football question is this analysis trying to answer?"

rather than:

> "What chart can we build?"

---

## Development workflow

For every significant feature use this workflow:

1. Football analysis
2. Data requirements
3. Technical design
4. Implementation
5. Automated tests
6. Review
7. Documentation

Do not skip the analytical stage.

---

## Project documentation

Important decisions must be documented.

Use:

- `PROJECT.md` for project objectives and scope
- `ROADMAP.md` for planned work
- `docs/ARCHITECTURE.md` for architecture
- `docs/FOOTBALL_ANALYTICS.md` for analytical methodology
- `docs/DECISIONS.md` for important technical and analytical decisions
- `docs/DATA_PROVIDERS.md` for provider evaluations and licensing

---

## Code quality

Prefer:

- clear code;
- small modules;
- type hints;
- meaningful names;
- explicit error handling;
- automated tests;
- documentation for non-obvious logic.

Avoid:

- huge files;
- duplicated logic;
- unexplained magic numbers;
- premature optimization;
- unnecessary abstractions.

---

## Git

Use small, meaningful commits.

Commit messages should describe the change.

Examples:

- `feat: add player data ingestion`
- `feat: calculate player per90 metrics`
- `test: add player metric tests`
- `docs: document xG methodology`

---

## Agent collaboration

Specialized agents may be used for:

- football analysis;
- data science;
- data engineering;
- backend;
- frontend;
- QA.

The lead agent is responsible for maintaining consistency between them.

Before changing an existing architecture decision, inspect the relevant documentation.

---

## Important instruction

Do not attempt to build the entire application in one operation.

Build incrementally.

Each phase should produce a working and testable result before moving to the next phase.

---

## Data provider architecture

The application must be provider-agnostic.

Never couple the analytics layer, API or frontend directly to a specific external data provider.

External providers must be implemented behind a provider interface/adapter.

Conceptually:

```text
External Provider
       ↓
Provider Adapter
       ↓
Canonical Football Data Model
       ↓
Analytics Layer
       ↓
API
       ↓
Frontend
```

Examples of potential providers:

- StatsBomb Open Data;
- StatsBomb commercial data;
- Wyscout
- Opta;
- Sportradar.

The first implementation may use StatsBomb Open Data.

However, this must be considered an implementation detail rather than a fundamental architectural dependency.

Provider-specific fields must not leak throughout the application.

If a provider offers a metric that cannot be represented in the canonical model, document the limitation rather than creating undocumented provider-specific logic.

When evaluating a new provider, consider:

- licensing;
- freshness;
- coverage;
- event granularity;
- player identifiers;
- team identifiers;
- competition identifiers;
- historical coverage;
- tracking availability;
- API limits;
- cost;
- redistribution restrictions.

### Data licensing and provider rules

Current initial source: StatsBomb Open Data (see `docs/DECISIONS.md` D002, D004).

- Never commit raw or event-level provider data to the repository. `data/` is gitignored; tests use small synthetic fixtures.
- Every published output (screenshot, demo page, write-up) must attribute the data source (StatsBomb logo for StatsBomb data).
- A public demo may expose derived/aggregated analytics only, never raw or bulk event data.
- Never use open data for commercial purposes.
- Never scrape FBref, Understat, WhoScored, Sofascore, FotMob or similar sites (D008).
- Analytics must check `ProviderCapabilities` before using a provider-dependent concept (pressures, xG, birth date…). Unavailable means unavailable, not zero.
- Provider metrics (xG, OBV…) are always source-tagged and never substituted across providers (D007).
