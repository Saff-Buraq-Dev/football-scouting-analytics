# Data Provider Evaluation

Phase 1A deliverable. Research date: **2026-10-04**.

Phase 1B verification update: **2026-10-04** (coverage audit and licence checks). See [data/STATSBOMB_COVERAGE.md](data/STATSBOMB_COVERAGE.md).

This document evaluates free and commercial football data providers against the 16 criteria the project requires. It supports the decisions recorded in [DECISIONS.md](DECISIONS.md) (D002, D003, D004, D008, D009) and the architecture in [ARCHITECTURE.md](ARCHITECTURE.md).

> **Not legal advice.** Licence readings below are deliberately conservative. Where something is marked *(verify)* it must be confirmed in Phase 1B (or with the provider) before we rely on it.

---

## 1. Assumptions

1. The developer is an **individual**, not a club or company, with no commercial data contract.
2. The project will eventually be **publicly visible** (public repository, screenshots, possibly a deployed demo).
3. Data budget is **€0** until there is a concrete reason to spend (e.g. a club engagement).
4. In professional use, a club would supply **its own licensed feed**. The platform never resells or redistributes data.
5. **Tracking data is out of scope** until Phase 9. Event data is the core of the platform.

---

## 2. Use contexts

Licences treat these contexts very differently. Every provider below is assessed against all four.

| Context | What it means in this project |
|---|---|
| **Learning** | Private notebooks and experiments on a local machine. Nothing published. |
| **Personal development** | Running the application locally. Nothing published. |
| **Portfolio / public demonstration** | Public GitHub repository, screenshots, blog posts, a publicly deployed demo, showing the project to a club in an interview. |
| **Commercial** | Paid work, use inside a club or company, any monetised product or service. |

Open data being free to *download* does **not** mean it is free to *redistribute* or to *use commercially*.

---

## 3. Glossary (for readers new to football data)

| Term | Meaning |
|---|---|
| **Event data** | A log of on-ball actions (pass, shot, tackle…) with time, player, team, outcome and pitch coordinates. Typically ~3,000–4,000 events per match. Collected by human operators watching video. |
| **Tracking data** | x/y positions of *all* 22 players and the ball, 10–25 times per second. Either from in-stadium optical cameras (TRACAB, Second Spectrum, Hawk-Eye) or derived from TV broadcast (SkillCorner, PFF). |
| **Freeze frame / 360** | StatsBomb's middle ground: the positions of visible players at the moment of each event, captured from broadcast video. |
| **xG (expected goals)** | Probability that a shot becomes a goal, from a model trained on historical shots (distance, angle, body part, situation…). **Each provider has its own model**, so values are not interchangeable. |
| **xA / xAG** | xG of the shot that a pass led to, credited to the passer. Definitions differ by provider. |
| **OBV / possession value** | Models that value every action by how much it changes the probability of scoring or conceding. Proprietary per provider. |
| **Packing** | IMPECT's metric: number of opponents bypassed by a pass or dribble. |

---

## 4. Open / free sources

### 4.1 StatsBomb Open Data (Hudl StatsBomb) — **recommended initial source**

Source: <https://github.com/statsbomb/open-data> (JSON, the same format as the commercial StatsBomb API).

| # | Criterion | Assessment |
|---|---|---|
| 1 | Freshness | Static releases. No live or weekly updates. Most recent club seasons: 2023/24. Recent tournaments: Euro 2024, Copa América 2024, Women's Euro 2025. |
| 2 | Historical coverage | Mixed. Some matches from the 1950s–1980s (World Cups, Champions League finals), plus the 2004–2021 La Liga seasons (Barcelona/Messi matches). |
| 3 | Competition coverage | ~40 competition-seasons. **Men:** **complete** 2015/16 Premier League, La Liga, Serie A (380 each) and Ligue 1 (377/380). **1. Bundesliga 2015/16 is Leverkusen-only (34 matches)**, so it is *not* the complete Big-5. Partial (single team): La Liga 2004/05–2020/21 except 2015/16 (Barcelona), Bundesliga 2023/24 (Leverkusen), Ligue 1 2021/22–2022/23 (PSG), MLS 2023 (Inter Miami, 6 matches), Premier League 2003/04 (Arsenal); FIFA World Cup 2018 & 2022; Euro 2020 & 2024; Copa América 2024; AFCON 2023; selected Champions League finals. **Women:** complete 2023/24 WSL, Liga F, Frauen-Bundesliga, Serie A Women and NWSL 2023 (771 matches, 62 teams, ~1,500 players, released 27 May 2026); earlier WSL seasons; Women's World Cup 2019 & 2023; Women's Euro 2022 & 2025. |
| 4 | Player coverage | All players appearing in covered matches: name, nickname, nationality, shirt number, positions played with time spells. **No date of birth, height, foot, contract or market value.** |
| 5 | Team coverage | All teams in covered matches: name, country, gender, managers per match. |
| 6 | Event-level data | Yes. The richest open specification: passes, shots, carries, pressures, duels, dribbles, ball recoveries, goalkeeper actions, with related-event links and possession sequences. |
| 7 | Event coordinates | Yes. 120 × 80 pitch units. Each team attacks left→right. Start and end locations, plus 3-D shot end location. |
| 8 | Tracking | No continuous tracking. **360 freeze frames** for 12 competition-seasons (e.g. WC 2022, Euro 2020/2024, Bundesliga 2023/24, La Liga 2020/21, Ligue 1 2021–23, MLS 2023, WWC 2023, W-Euro 2022/2025, AFCON 2023). |
| 9 | xG / xA / advanced | StatsBomb xG on every shot, plus a per-shot freeze frame (player positions at the shot) in all seasons. No OBV. No explicit xA field, but it can be derived from the xG of the shot a pass assisted (see [FOOTBALL_ANALYTICS.md](FOOTBALL_ANALYTICS.md)). |
| 10 | Identifiers | Stable numeric ids for competition, season, match, team, player and event (UUID). The same ids are used in the commercial API. |
| 11 | API availability | No API: static files on GitHub. The Python client `statsbombpy` reads them. |
| 12 | API limitations | GitHub raw-file access only. Full download is several GB. |
| 13 | Licensing | **StatsBomb Public Data User Agreement** (last updated 8 Sep 2023). Data is for "analysis, research and to facilitate the shared ideas & understanding". The user **may not** "edit, distort, distribute, reproduce, sell or in any way provide the data to any external or third party" (§1.2.1) and may not "commercially exploit the data or any analysis derived from the use of the Service" (§1.2.2). Published analysis **must carry the StatsBomb logo** (§1.4). StatsBomb may withdraw the service at any time (§2.1). Users are asked to register at statsbomb.com/resource-centre. |
| 14 | Cost | Free. |
| 15 | Portfolio suitability | **High**, with conditions: publish *analysis* (charts, derived per-90 metrics, write-ups) carrying the logo. **Do not** commit raw data to the repository. **Do not** expose a public API or download that serves event-level data. |
| 16 | Professional suitability | **None for commercial use** (§1.2.2). It *is* the best way to build a codebase that can later consume commercial StatsBomb data, because the schema is the same. |

| Learning | Personal dev | Portfolio | Commercial |
|---|---|---|---|
| ✅ | ✅ | ✅ with logo, no raw-data redistribution | ❌ |

### 4.2 Wyscout public dataset (Pappalardo et al., 2019)

Source: figshare collection 4415000. Paper: *A public data set of spatio-temporal match events in soccer competitions*, Scientific Data 6:236 (2019).

| Criterion | Assessment |
|---|---|
| Freshness / history | Static, 2017/18 season (Euro 2016, World Cup 2018). |
| Coverage | **Complete seasons**: Premier League, La Liga, Serie A, Bundesliga, Ligue 1 2017/18, plus World Cup 2018 and Euro 2016 (~1,900 matches). Players include birth date, height, foot and role. |
| Events / coordinates | Yes, Wyscout v2 format: event + sub-event + tags, 0–100 grid with an inverted y-axis. |
| Tracking | No. |
| Advanced metrics | No xG. PlayeRank scores provided by the authors. |
| Identifiers | Wyscout ids (the same id family clubs use in commercial Wyscout). |
| API | Static files. |
| Licence | **CC BY 4.0** (verified via the figshare API, 2026-10-04). Citation required. Commercial use permitted with attribution. |
| Use contexts | Learning ✅ · Personal ✅ · Portfolio ✅ (attribution) · Commercial ✅ (attribution) |
| Portfolio / professional | **Very good second source** to prove provider-agnosticism (different schema, complete seasons, permissive licence). It is old data, so not useful for current scouting. |

### 4.3 IMPECT open data

Source: <https://github.com/ImpectAPI/open-data>. Bundesliga 2023/24 event data, event KPIs, lineups, substitutions, squads, KPI definitions. It includes packing / "bypassed opponents". **Licence verified (IMPECT Terms of Use, German law):** analytical/research use only; **no redistribution, no commercial use**, credit IMPECT on published insights, revocable at any time. Same restrictions as StatsBomb in practice. Useful as a third schema reference and for packing concepts. Portfolio ✅ (with credit, no redistribution) · Commercial ❌.

### 4.4 Tracking samples (learning only)

| Source | Content | Terms |
|---|---|---|
| Metrica Sports sample data | 3 anonymised matches, synchronised tracking + events | "Acknowledge the source" for public use |
| SkillCorner open data | 10 A-League 2024/25 matches (broadcast tracking, dynamic events, phases of play) **plus season-level physical, off-ball-run and passing aggregates for the whole league** | **MIT licence** (repository), credit requested. The most permissive tracking source |
| PFF FC World Cup 2022 | All 64 matches, broadcast tracking + events + PFF grades | Access by request. Terms still to verify, **deferred to Phase 9** (D009) |

Useful for Phase 9 experiments. Too small or anonymised for player scouting.

### 4.5 Low-cost / free "aggregator" APIs

football-data.org (free tier), API-Football, Sportmonks (€29 / €99 / €249 per month for 5 / 30 / 120 leagues; xG only as an add-on). They give **current** fixtures, results, lineups and basic statistics, but no rich event coordinates. They could later provide a "current season context" feed. They are not a basis for event analytics.

### 4.6 Excluded sources

| Source | Reason |
|---|---|
| FBref / Stathead | Basic historical stats only. **Opta terminated FBref's advanced data feed on 2026-01-20** and required deletion. Scraping is against Sports Reference terms. |
| Understat, WhoScored, Sofascore, FotMob, Transfermarkt | Terms of service forbid scraping. Underlying data is licensed from commercial providers. |

The FBref case shows that **access to provider data can be withdrawn without notice**. The adapter boundary (see [ARCHITECTURE.md](ARCHITECTURE.md)) limits the damage when that happens.

---

## 5. Commercial providers

Public pricing is rare in this market. "Quote" means the provider publishes no prices. All of them sell to organisations. An individual may not be able to buy a licence at all.

| # | Criterion | Hudl StatsBomb | Hudl Wyscout | Opta / Stats Perform | Sportradar |
|---|---|---|---|---|---|
| 1 | Freshness | Post-match within hours, plus live products | Post-match | Live + post-match | Live, betting-grade latency |
| 2 | Historical coverage | Deep for major leagues (back to ~2013+ in many) | Many seasons, broad | Deepest (decades for top leagues) | Broad, mostly results/timeline history |
| 3 | Competition coverage | ~100+ competitions incl. women's | **600+ competitions**: best breadth incl. lower leagues and youth | ≈3,900 competitions (all data levels) | Very broad (official league deals) |
| 4 | Player coverage | Full squads, bios | Very broad player database (scouting focus) incl. DOB, contracts, agents | Full | Full squads |
| 5 | Team coverage | Full | Full | Full | Full |
| 6 | Event data | **Richest spec** (pressures, carries, related events) | Yes (v3) | Yes (F24 / MA3, qualifier-based) | Event timeline, less granular |
| 7 | Coordinates | Yes, 120 × 80 | Yes, 0–100 | Yes, 0–100 | Limited compared with the others |
| 8 | Tracking | 360 freeze frames; tracking via partners | No | Opta Vision / partners | Limited |
| 9 | xG / advanced | xG, OBV, HOPS (2026), set-piece model | xG, xA, progressive actions, indices | xG, xA, possession value | Basic |
| 10 | Identifiers | StatsBomb ids (= open data) | Wyscout ids (widely used by clubs) | Opta ids (industry de-facto standard) | Sportradar URNs |
| 11 | API | REST API + StatsBomb IQ platform | REST API (sold **separately** from platform seats) | Stats Perform SDAPI / feeds | Soccer API v4 (REST + push) |
| 12 | API limits | Contract-defined | Contract-defined | Contract-defined | Trial key: low monthly quota and rate limits |
| 13 | Licensing | Contract; redistribution restricted | Contract; platform seat ≠ data rights | Contract; strict enforcement (FBref case) | Contract; strong betting focus |
| 14 | Cost | Quote | Quote (Copper / Mercury / Gold / Diamond tiers) | Quote. Third-party reports start "from ~€250/month" for narrow media feeds | Free trial; reported ~€1.3k+/month for production |
| 15 | Portfolio fit | Low: no individual licence likely, and outputs can't be shared publicly without permission | Low/medium: a platform seat gives insight but not API/redistribution rights | Low | Trial for learning only; not public use |
| 16 | Professional fit | **Excellent**: deepest event model, same schema as our first adapter | **Excellent for scouting breadth**; most common club platform | **Excellent**: market standard for media and many clubs | Good for live/fixtures; weak for deep analytics |

### Specialist providers (later, if needed)

- **IMPECT**: packing-based event data (Bundesliga-centric).
- **SkillCorner**: broadcast tracking and physical data at scale.
- **Second Spectrum (Genius Sports), TRACAB, Hawk-Eye**: optical tracking, stadium-level, enterprise only.

---

## 6. Recommendations

1. **Initial dataset: StatsBomb Open Data.** It has the richest free event model, provider xG, 360 for recent tournaments, mature tooling (statsbombpy, kloppy, mplsoccer), and the same schema as the leading commercial event product. The exact analysis slice is chosen in Phase 1B from the coverage audit ([data/STATSBOMB_COVERAGE.md](data/STATSBOMB_COVERAGE.md)): complete men's 2015/16 Premier League, La Liga, Serie A and Ligue 1; complete women's 2023/24 leagues; or tournaments.
2. **Future commercial provider: Hudl StatsBomb** is the first candidate, because of schema continuity and event depth. **Opta** is the main alternative (market standard). **Wyscout** is the alternative when breadth across many leagues matters more than event depth (typical recruitment use). **No purchase is recommended now.** Realistically, access would come through a club's own licence.
3. **Design for several providers, implement one.** Build only the StatsBomb adapter first. Validate the canonical model on paper against the Wyscout v2 and Opta event schemas. Optionally, add a second open adapter (Wyscout public 2017/18) later to demonstrate provider-agnosticism with no licensing risk.

---

## 7. Sources

- StatsBomb open data repository and `LICENSE.pdf` — <https://github.com/statsbomb/open-data>
- Hudl StatsBomb free women's leagues release — <https://www.hudl.com/blog/statsbomb-free-womens-data-wsl-ligaf-bundesliga-seriea-nwsl>
- FBref advanced data removal — <https://www.sports-reference.com/blog/category/fbref/>, <https://amp.awfulannouncing.com/soccer/sports-reference-pulls-advanced-data-agreement-violation-dispute.html>
- Wyscout public dataset — <https://figshare.com/collections/_/4415000>
- IMPECT open data — <https://github.com/ImpectAPI/open-data>
- Metrica sample data — <https://github.com/metrica-sports/sample-data>
- SkillCorner open data — <https://github.com/SkillCorner/opendata>
- PFF FC World Cup 2022 dataset — <https://www.blog.fc.pff.com/blog/enhanced-2022-world-cup-dataset>
- Sportradar trial/pricing — <https://sportsapis.dev/apis/sportradar>, <https://developer.sportradar.com/football/docs/ig-account-maintenance>
- Stats Perform licensing FAQ — <https://www.statsperform.com/faqs/stats-perform-faqs-pricing-licensing/>
- Wyscout pricing tiers — <https://www.hudl.com/en_gb/products/wyscout/pricing>
- Sportmonks pricing — <https://www.sportmonks.com/football-api/plans-pricing>
