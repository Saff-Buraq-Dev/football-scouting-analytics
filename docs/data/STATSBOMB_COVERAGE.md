# StatsBomb Open Data — Coverage Audit

Phase 1B deliverable. Audit date: **2026-10-04**.
Source: `statsbomb/open-data` pinned at commit `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb` (80 competition-seasons, 3,961 matches).

Reproduce with:

```bash
cd scripts/discovery && python3 statsbomb_coverage_audit.py
```

---

## 1. Football question

> For which competition-seasons is the data a **complete population** of matches?

This matters because per-90 comparisons, percentiles and league averages are only meaningful when every team and player in the competition is observed under the same conditions (see [FOOTBALL_ANALYTICS.md](../FOOTBALL_ANALYTICS.md), "Data coverage and reference populations").

## 2. Method

Only the match files are used, with no event data. For each competition-season:

| Evidence | Meaning |
|---|---|
| Matches, teams | Size of the dataset |
| **Focal-team share** | Share of matches involving the most frequent team. **100 % means every match involves one team.** |
| Matches per team (min–median–max) | In a complete league season, all teams play (almost) the same number of matches |

Heuristic flag (it only flags; the final `coverage_scope` below is a reviewed decision):

- `single_team`: focal-team share = 100 % (and > 1 match);
- `balanced`: min matches/team ≥ 90 % of max (league-like);
- `unbalanced`: everything else (tournaments with knockouts, isolated finals, or partial data).

Expected totals are derived from structure. A double round-robin league with *n* teams has *n·(n−1)* matches.

**Limitation:** The audit checks *which matches* exist, not whether each match's events are complete. Event-level completeness checks belong to the Phase 2 validation tests.

## 3. Results — usable as complete populations

### Men's club leagues
| Competition | Season | Matches | Expected | Teams | 360 | coverage_scope |
|---|---|---:|---:|---:|---|---|
| Premier League | 2015/16 | 380 | 380 | 20 | – | **complete** |
| La Liga | 2015/16 | 380 | 380 | 20 | – | **complete** |
| Serie A | 2015/16 | 380 | 380 | 20 | – | **complete** |
| Ligue 1 | 2015/16 | 377 | 380 | 20 | – | **complete (3 matches missing)** |
| Indian Super League | 2021/22 | 115 | 110 league + playoffs | 11 | – | complete *(structure consistent; low relevance)* |

### Women's club leagues
| Competition | Season | Matches | Expected | Teams | 360 | coverage_scope |
|---|---|---:|---:|---:|---|---|
| FA WSL | 2023/24 | 132 | 132 | 12 | – | **complete** |
| Liga F | 2023/24 | 240 | 240 | 16 | – | **complete** |
| Frauen-Bundesliga | 2023/24 | 132 | 132 | 12 | – | **complete** |
| Serie A Women | 2023/24 | 130 | 26 per team (regular season + poules) | 10 | – | **complete** |
| NWSL | 2023 | 137 | 132 regular + 5 playoff | 12 | – | **complete** (regular season balanced at 22) |
| FA WSL | 2020/21 | 131 | 132 | 12 | – | complete (1 missing) |
| FA WSL | 2019/20 | 87 | season curtailed (COVID-19) | 12 | – | complete-as-played, **unbalanced** |
| FA WSL | 2018/19 | 107 | 110 | 11 | – | complete (3 missing) |

### International tournaments (complete, but small samples per team: 3–7 matches)
| Competition | Season | Matches | 360 |
|---|---|---:|---|
| FIFA World Cup | 2022 | 64 | yes |
| FIFA World Cup | 2018 | 64 | – |
| UEFA Euro | 2024 | 51 | yes |
| UEFA Euro | 2020 | 51 | yes |
| Copa América | 2024 | 32 | – |
| Africa Cup of Nations | 2023 | 52 | yes |
| Women's World Cup | 2023 | 64 | yes |
| Women's World Cup | 2019 | 52 | – |
| UEFA Women's Euro | 2025 | 31 | yes |
| UEFA Women's Euro | 2022 | 31 | yes |

## 4. Results — partial (not valid as populations)

| Competition | Seasons | What is covered |
|---|---|---|
| **1. Bundesliga** | **2015/16**, 2023/24 (360) | **Bayer Leverkusen matches only (34 each)**. This corrects the earlier assumption that the 2015/16 release covered the complete Big-5. |
| La Liga | 2004/05–2014/15, 2016/17–2020/21 (2020/21 with 360) | Barcelona matches only (7–38 per season) |
| Ligue 1 | 2021/22, 2022/23 (360) | Paris Saint-Germain matches only |
| Major League Soccer | 2023 (360) | Inter Miami, 6 matches |
| Premier League | 2003/04 | Arsenal matches only (38) |
| Champions League | 1970/71–2018/19 (17 seasons) | Final only (1 match each) |
| FIFA World Cup | 1958, 1962, 1970, 1974, 1986, 1990 | 1–6 historical matches |
| Others | Copa del Rey, Liga Profesional, NASL 1977, Serie A 1986/87, UEFA Europa League 1988/89, FIFA U20 WC 1979 | 1–3 historical matches |
| NWSL | 2018 | 36 matches, unbalanced (5–13 per team) |

These seasons are still valuable for **single-player or single-team analysis** (e.g. "how did Barcelona's build-up evolve 2008–2015?"). They must **not** feed percentiles or league rankings.

## 5. Implications

1. **Men's complete club data = four leagues in one season (2015/16), 1,517 matches.** It allows cross-league percentiles within a single season, but it is ten years old.
2. **Women's complete club data = five leagues (2023/24 / 2023), 771 matches.** It is recent and complete, the best basis for a "current-like" scouting demo.
3. **360 freeze frames exist only for tournaments and partial seasons.** They are not available for any complete league season. 360-based analysis is a Phase 9 tournament feature.
4. Every shot event carries its **own shot freeze frame** (player positions at the shot), even in 2015/16 (see the data dictionary). This is independent of 360.
