# Football Analytics Methodology

This document contains the analytical methodology used by the application.

No metric should be implemented without documenting its definition and limitations.

---

## Metric documentation format

For every metric document:

### Metric name

Definition:

Formula:

Data required:

Football interpretation:

Why it matters:

Limitations:

Potential biases:

---

## Data sources and provenance

Every metric must state **which data source it was computed from**. See [DATA_PROVIDERS.md](DATA_PROVIDERS.md) and decision D007 in [DECISIONS.md](DECISIONS.md).

### Provider metrics are not interchangeable

Expected goals (xG) is a *model output*, not an observed fact. StatsBomb, Opta and Wyscout each train their own xG model with different inputs. For example, StatsBomb uses freeze-frame information such as goalkeeper position. The same shot can therefore have different xG values.

Rules:

- A provider metric is always labelled with its source (e.g. "xG (StatsBomb)").
- Players or teams are only compared on a provider metric when **all values come from the same provider and model**.
- If a metric is missing for a source, it is shown as *unavailable*, never as zero and never replaced by another provider's value.

### Event definitions differ between providers

Providers disagree on what counts as a "dribble", "duel", "key pass", "pressure" or "progressive pass". Some concepts exist in only one provider: StatsBomb records pressures and carries, Wyscout v2 does not. The canonical event taxonomy is documented in [ARCHITECTURE.md](ARCHITECTURE.md), and each adapter documents its mapping. A metric defined on canonical events inherits the limitations of that mapping.

### xA (expected assists)

StatsBomb open data has no xA field. If implemented, xA would be **derived**: the StatsBomb xG of a shot, credited to the player whose pass assisted it (StatsBomb links the pass to the shot). This is a derived metric with a documented definition, not a provider value. Other providers' "xA" may be defined differently, for example including passes that did not lead to a shot.

---

## Data coverage and reference populations

Population-based metrics (percentiles, rankings, league averages) are only valid when the population is **complete**.

Several StatsBomb open-data seasons contain **only the matches of one team** (e.g. La Liga seasons containing Barcelona matches only). In such a season:

- the players of that team appear in every match, while opponents appear once or twice;
- comparing per-90 values across players from that season is biased, because opponents are seen only against one (usually dominant) team;
- percentiles computed on that population are **not meaningful**.

Rules:

- Each season carries a `coverage_scope` (`complete` / `partial`). See [ARCHITECTURE.md](ARCHITECTURE.md).
- Percentiles and rankings are computed only on `complete` seasons, unless the user explicitly accepts a warning.
- Tournament data (World Cup, Euro) has a natural small-sample problem: a team plays at most 7 matches. Minimum-minute thresholds matter even more there.
- The season and competition of every analysis must be visible to the user. The open data is **historical**: it describes past seasons, not current form.

---

## Minutes played

Per-90 metrics depend on minutes played, and providers rarely supply it directly. It will be **derived** from canonical lineups and events:

- starters enter at 0:00 of period 1;
- substitutes enter at their substitution time;
- players leave at substitution, red card (straight or second yellow) or end of match;
- **actual period lengths including stoppage time** are used (from period end events), not a fixed 45 minutes;
- extra-time periods count as played minutes.

Implemented in Phase 2 for StatsBomb (see [data/STATSBOMB_MAPPING.md](data/STATSBOMB_MAPPING.md) §6):

- minutes are measured to the second from the provider's position spells;
- **time off the pitch for treatment is not counted** (StatsBomb records "Player Off" / "Player On"), so a player treated for one minute in a full match plays slightly less than the match length;
- when lineup data contradicts substitution or dismissal events, the **events win** (decision D014);
- every match is validated: no team may exceed 11 players × match length.

Interpretation: a "full match" is typically 92–98 minutes, not 90, because stoppage time is included. Per-90 values computed this way are therefore slightly lower than those from sources using a nominal 90 minutes per match. Minutes from different providers may differ slightly because their period timings differ.

---

## Pitch coordinates

Canonical coordinates are metres on a **standard 105 × 68 pitch** (decision D005). Real pitches vary between roughly 100–110 m long and 64–75 m wide, and providers rarely supply actual dimensions. Distance-based definitions (e.g. "a pass moving the ball at least 10 m towards goal") are therefore **approximate**, and thresholds should not be read with false precision.

---

## Per-90 metrics

Per-90 statistics should generally be calculated as:

metric_per90 = metric_total / minutes_played * 90

However, per-90 statistics should not automatically be interpreted as superior to totals.

Small samples can produce misleading results.

Where appropriate, the application should enforce minimum-minute thresholds.

---

## Percentiles

Percentiles may be useful when comparing players against a relevant population.

The comparison population must always be documented.

Examples:

- all midfielders;
- central midfielders;
- forwards;
- players in a specific competition.

A percentile without a defined reference population is not meaningful.

---

## Player comparison

Player comparisons should consider:

- position;
- playing time;
- role;
- competition;
- team context;
- sample size.

Simple statistical ranking should not be presented as definitive proof that one player is better than another.

---

## Player similarity

Player similarity must use a documented statistical methodology.

Arbitrary similarity percentages are not acceptable.

The methodology should document:

- variables;
- normalization;
- weighting;
- distance/similarity function;
- reference population;
- limitations.
---

# Phase 4 — Player season metrics (v1)

Status: implemented in `src/football_platform/analytics/` (decision D016). Data: D011 slice (2015/16 Premier League, La Liga, Serie A, Ligue 1).

## Football questions

The first metric set answers basic recruitment questions about a player's season:

1. **How much did he play?** Minutes, appearances, starts: the sample behind every other number.
2. **How dangerous is he in front of goal?** Shot volume, chance quality (npxG), finishing output.
3. **Does he create chances for others?** Key passes, assists, xA.
4. **Does he move the ball towards goal?** Progressive passes and carries, passes into the final third and the box.
5. **What does he contribute without the ball?** Tackles, interceptions, recoveries, pressures, aerial duels.
6. **How does he compare with players in the same role?** Percentiles within a documented reference population.

## Unit of analysis

**Player × competition-season.** A player who changed clubs within the same league is aggregated across both clubs (the clubs are listed). A player who moved league mid-season appears once per competition.

## Global rules

| Rule | Value | Reason |
|---|---|---|
| Shoot-out (period 5) | excluded everywhere | not part of match play |
| Penalties | excluded from npxG, non-penalty goals and shots; penalty goals reported separately | penalty takers would dominate xG and goals, but taking penalties is a role, not open-play quality |
| Own goals | never credited to the scorer as goals | |
| Minimum minutes for per-90 and percentiles | **900** (≈ 10 full matches) | below this, per-90 values are unstable. Configurable |
| Per-90 formula | `total / minutes_played × 90` | minutes include stoppage time (see "Minutes played") |
| Reference population | complete seasons only (D010), same season, same **position group**, ≥ 900 min | |

## Position groups (reference populations)

A player's **primary role** for the season is the canonical role with the most minutes, from position spells. Roles are grouped as follows:

| Group | Roles | Football rationale |
|---|---|---|
| Goalkeeper | GK | |
| Centre-back | CB | |
| Full-back | FB, WB | wide defenders; wing-backs are more attacking, which is a known limitation |
| Central midfield | DM, CM | |
| Attacking midfield / winger | AM, WM, W | creative and wide attacking roles. "Right Midfield" in a 4-4-2 often plays like a winger |
| Striker | CF | |

**Limitation:** StatsBomb positions are formation slots, not roles. A defensive "CM" and a box-to-box "CM" end up in the same group. Groups describe *where* a player was deployed, not *how* he played.

## Metric definitions

Notation: completed = canonical `outcome = success`. Coordinates are in canonical metres (attacking towards x = 105). `goal = (105, 34)`.

### Playing time

| Metric | Definition |
|---|---|
| `minutes` | sum of `appearances.minutes_played` |
| `appearances` | matches with minutes > 0 |
| `starts` | `is_starter` |

### Shooting

| Metric | Formula | Data | Limitations |
|---|---|---|---|
| `np_shots` | shots with `set_piece ≠ penalty` | events | volume ignores quality |
| `np_goals` | np_shots with `shot_outcome = goal` | events | small numbers; noisy over one season |
| `penalty_goals` | penalty shots scored | events | |
| `npxg` | Σ provider xG of np_shots | `provider_metrics` (StatsBomb xG) | **capability-gated** (`has_provider_xg`); a model output, valid only within StatsBomb data (D007) |
| `npxg_per_shot` | npxg / np_shots | | shot selection; unstable below ~20 shots |

Football interpretation: npxG per 90 measures how often and how well a player gets into scoring positions. Over one season it predicts future goals better than goals do. Goals minus xG is **not** reported in v1: over a single season it is dominated by noise.

### Chance creation

| Metric | Formula | Limitations |
|---|---|---|
| `assists` | completed passes with `pass_is_goal_assist` | depends on the teammate finishing |
| `key_passes` | passes with `pass_is_shot_assist` **or** `pass_is_goal_assist` (the pass directly before a shot) | ignores how good the chance was |
| `xa` | Σ xG of the shots that the player's passes assisted (`pass_assisted_shot_event_id` → shot xG), penalties excluded | **derived metric**, not a provider value. Capability-gated by `has_provider_xg`. Other providers define xA differently (e.g. including passes that did not lead to a shot) |

### Ball progression

**Progressive pass/carry** (Wyscout-style definition, applied to canonical coordinates): a completed pass (or carry) moving the ball closer to the opponent's goal centre by at least:

| Start and end | Required gain in distance to goal |
|---|---|
| both in own half (x < 52.5) | 30 m |
| from own half into opponent half | 15 m |
| both in opponent half | 10 m |

| Metric | Formula | Limitations |
|---|---|---|
| `progressive_passes` | completed progressive passes, excluding set pieces | ignores pass difficulty; standard pitch approximation (D005) |
| `progressive_carries` | progressive carries | **capability-gated** (`has_carries`, StatsBomb only) |
| `passes_into_final_third` | completed passes starting at x < 70 and ending at x ≥ 70 (final third = last 35 m), excluding set pieces | |
| `passes_into_box` | completed passes ending in the penalty area (x ≥ 88.5, \|y − 34\| ≤ 20.16), not starting in it, excluding set pieces | |
| `passes_attempted`, `pass_completion` | passes with outcome success/fail (excludes unknown and not_applicable such as injury clearances); completion = completed / attempted | **completion reflects role and risk, not quality**: centre-backs passing sideways complete more than creative players |

### Defending

| Metric | Formula | Limitations |
|---|---|---|
| `tackles` / `tackles_won` | ground duels (StatsBomb tackles) / with outcome success | |
| `interceptions` | interception events | |
| `ball_recoveries` | successful ball recoveries | |
| `pressures` | pressure events | **capability-gated** (`has_pressure_events`) |
| `aerials_won`, `aerials_lost`, `aerial_win_pct` | events flagged `aerial_won` / aerial duels lost / won ÷ (won + lost) | StatsBomb records wins as flags (data dictionary §3.6) |

**Major limitation, defensive volume and possession:** a team that has the ball less makes more defensive actions. Raw defensive per-90 values therefore partly measure the team's style, not the player. **Possession adjustment is not applied in v1** and is planned as the next methodological step. Until then, defensive percentiles must be read with this caveat.

## Percentiles

`percentile = rank of the player's value within the reference population, scaled to 0–100` (ties receive their average rank, so the best player in a population of 100 gets 100 and the median about 50).

- Computed on per-90 values, ratios and shares only, for players meeting the minutes threshold.
- The output always states the reference population: seasons, position group, minutes threshold, population size.
- A percentile is **descriptive**: "higher than X % of comparable players in this sample". It is not a quality rating. A high defensive-actions percentile can mean a player defends a lot because his team rarely has the ball.

### Known limitations of v1

- One season of data per player. No trend, no age (no birth dates).
- League strength is not adjusted: percentiles pool four leagues of similar level but do not claim they are equal.
- Team context (style, possession, quality of teammates) is not adjusted.
- Ratios (pass completion, xG per shot, aerial win %) are unstable for players with few attempts. A minimum-attempts rule is a planned refinement.

## Validation of v1 on real data (2026-10-04)

Report: `python -m football_platform.reports.player_season_report` → `data/analytics/player_seasons.{parquet,csv}`. Result: 2,214 player-seasons, of which 1,364 meet the 900-minute threshold.

| Check | Result |
|---|---|
| Goal conservation: player goals + own goals = sum of match scores | 3,869 + 128 = **3,997 = 3,997** |
| Known season totals (league, 2015/16) | Higuaín 36 (33 + 3 pens), Suárez 40, Kane 25, Özil 19 assists: match the public record |
| Assist counts | StatsBomb: Di María 17, Suárez 15. Public sources often cite 18 and 16. **Assist definitions differ between data providers** (deflected passes, penalties won…), so assist totals must always be read with their source (D007) |
| Face validity of leaders | npxG/90 strikers: Benzema, Higuaín, Suárez, Ibrahimović. xA/90 creators: Di María, De Bruyne, Neymar, Özil. Progressive passes/90 midfielders: Fàbregas, Carrick, Verratti, Jorginho |

Population sizes (eligible players per position group, four leagues pooled): attacking midfield/winger 275, central midfield 299, centre-back 262, full-back 254, striker 174, goalkeeper 100.

Observed limitations to address next:

1. **Small samples near the threshold**: e.g. Pastore (909 min) ranks 2nd for progressive passes/90. The output shows minutes next to every value; a stricter threshold or shrinkage towards the group mean are candidate refinements.
2. **Ratios on few attempts**: aerial win % of centre-backs with few aerial duels is unstable. A minimum number of attempts per ratio is planned.
3. **Possession adjustment of defensive metrics** (see "Defending").
4. **Goalkeepers** need their own metrics (shot-stopping, claims, distribution). The v1 outfield metrics say little about them.

---

# Phase 4.1 — Methodological refinements

Status: implemented (decision D017). Addresses the limitations observed in the v1 validation.

## 1. Minimum attempts for ratios

**Question:** when is a percentage (pass completion, aerial win %, npxG per shot) informative enough to rank?

For a success rate *p* measured on *n* attempts, the standard error is `√(p(1−p)/n)`. At p = 0.5:

| n | standard error | 95 % interval |
|---|---|---|
| 10 | 0.16 | ± 31 pts |
| 30 | 0.09 | ± 18 pts |
| 100 | 0.05 | ± 10 pts |

Rule: the ratio value is always shown, but **ranked (percentile) only when the denominator reaches a minimum**:

| Ratio | Minimum | Rationale |
|---|---|---|
| `pass_completion` | 100 passes attempted | ±10 pts |
| `long_pass_share` | 100 passes attempted | as above |
| `aerial_win_pct` | 30 aerial duels | ±18 pts. Stricter would remove most full-backs and midfielders |
| `npxg_per_shot` | 20 non-penalty shots | mean of a skewed distribution; below ~20 shots one big chance dominates |
| `gk_np_save_pct` | 40 non-penalty shots on target faced | ±14 pts at p = 0.7; ≈ 10 matches |

A `<ratio>_reliable` flag states whether the minimum is met.

## 2. Possession and defensive actions: context, not adjustment

**Question:** how much does a player defend *given how often his team was without the ball*?

A team with 65 % possession gives its players fewer chances to tackle or intercept than a team with 35 %. A possession adjustment was therefore planned.

**Possession proxy:** team share of the passes attempted in the match (both teams, shoot-out excluded). This is the FBref definition, and it works for any provider.

### Evaluated: the PAdj sigmoid

`factor = 2 / (1 + exp(−0.1 × (poss% − 50)))`, applied per match. This is the adjustment popularised in public analytics by StatsBomb.

### Evidence (D011 slice, `scripts/validation/phase41_validation.py`)

| Test | Result |
|---|---|
| Correlation, team possession vs team tackles + interceptions per match (80 team-seasons), raw | r = −0.22 |
| Same, after the PAdj sigmoid | **r = +0.87**: the adjustment massively over-corrects |
| Elasticity of actions to opponent possession (log-log, 3,034 team-matches) | tackles 0.25, interceptions 0.60, pressures 0.48, ball recoveries **−0.15** |
| Elasticity implied by the sigmoid | ≈ 1.7 for every action |
| Calibration at team-season level, fitted on PL + La Liga, tested on Serie A + Ligue 1 | tackles OK (−0.20 → −0.06); interceptions over-corrected (−0.39 → +0.20); pressures under-corrected (−0.77 → −0.40); recoveries no effect |

Interpretation: the possession effect exists but is modest and differs by action. Ball recoveries even *rise* with possession (counter-pressing teams win loose balls back). Possession is also confounded with team quality. One season of 80 teams is not enough to estimate a stable adjustment.

### Decision (D017)

- **No possession adjustment.** Defensive metrics stay raw.
- Every player-season carries **`team_possession_pct`**: his team's possession, weighted by his minutes in each match. Defensive values must be read next to it.
- To revisit when several seasons are available (more teams, within-team variation over time).

## 3. Goalkeeper metrics

**Question:** how well does a goalkeeper stop shots, deal with high balls and defend the space behind his defence?

Shots are attributed to the goalkeeper **on the pitch at the moment of the shot** (from canonical position spells with role GK, defending team). This is provider-independent.

| Metric | Definition | Limitations |
|---|---|---|
| `gk_np_sot_faced` | opponent non-penalty shots on target (outcome goal or saved) while on the pitch | "saved" includes saves of shots that were going wide |
| `gk_np_goals_conceded` | of which goals | own goals excluded |
| `gk_np_saves` | of which saved | |
| `gk_np_save_pct` | saves / shots on target faced | **does not account for shot difficulty**. The standard fix, post-shot xG (PSxG), is **not available in StatsBomb open data**, so "goals prevented" cannot be computed |
| `gk_claims` | goalkeeper actions of kind claim or punch | no denominator (crosses faced) in v1.1 |
| `gk_sweeper_actions` | goalkeeper actions of kind sweeper | |
| `long_pass_share` | passes ≥ 40 m / passes attempted | distribution style, not quality |

Goalkeeper metrics are reported **only for the goalkeeper position group** (NaN for outfield players).

## 4. Small samples: regressed estimates

**Question:** what is our best estimate of a player's *underlying* rate, given how many minutes we observed?

A per-90 value over 900 minutes contains a lot of luck. Empirical Bayes shrinkage pulls each player's observed rate towards the average of his position group, more strongly when he played less:

```
regressed = w × observed + (1 − w) × group_mean
w (reliability) = σ²_true / (σ²_true + noise_per_90 / exposure)
```

- `exposure` = minutes / 90.
- `noise_per_90` = group mean of Σ(contribution²) per 90 (compound-Poisson noise: for event counts this equals the mean rate; for xG it uses squared shot values).
- `σ²_true` = observed between-player variance of the rate − average noise variance (method of moments, estimated on the eligible players of the reference population; floored at a small positive value).
- Prior (group mean, σ²_true) is estimated on eligible players, then applied to **all** players of the group, including those under 900 minutes.

Outputs: `<metric>_p90_regressed` and `<metric>_reliability` (w, 0–1) for count metrics. If a metric has no event at all in a group (e.g. shots by goalkeepers), there is no noise and the observed value is kept (w = 1).

**Interpretation:** percentiles still describe *observed* performance. The regressed estimate is a *forecast-oriented* view: "what we expect from this player, knowing that low-minute samples are noisy". It is validated by checking whether it predicts the second half of the season better than the raw first-half rate.

**Limitations:** assumes players within a position group are exchangeable a priori (no age, league or team information). Ratios are not shrunk (they use minimum attempts instead).

## Validation of Phase 4.1 (2026-10-04)

Reproduce: `.venv/bin/python scripts/validation/phase41_validation.py`.

### Goalkeeping: goal accounting

3,569 non-penalty goals scored = **3,562** conceded by goalkeepers + **5** conceded while an outfield player was briefly in goal (goalkeeper metrics are reported only for the goalkeeper group) + **2** conceded with no goalkeeper on the pitch (keeper sent off, replaced by an outfield player not recorded as GK). Every goal is accounted for.

Leaders in non-penalty save % (≥ 40 shots on target faced): Buffon, Oblak, Trapp, Bravo, Enyeama. Juventus and Atlético had the best defensive records of the season.

### Regressed estimates predict better

First half of each season → second half (players with ≥ 450 minutes in each half; 1,057 player-seasons; minutes-weighted RMSE):

| Metric | RMSE raw | RMSE regressed | Improvement |
|---|---:|---:|---:|
| np_shots | 0.466 | 0.413 | 11 % |
| npxg | 0.071 | 0.062 | 12 % |
| key_passes | 0.384 | 0.346 | 10 % |
| xa | 0.056 | 0.048 | 14 % |
| progressive_passes | 0.990 | 0.926 | 7 % |
| passes_into_box | 0.369 | 0.341 | 8 % |
| interceptions | 0.715 | 0.654 | 8 % |
| tackles | 0.592 | 0.527 | 11 % |
| aerials_won | 0.670 | 0.654 | 2 % |

### How reliable is a per-90 value? (median reliability w, outfield players)

| Metric | ~900 min | ~2,700 min (full season) |
|---|---:|---:|
| progressive_passes | 0.80 | 0.93 |
| tackles | 0.65 | 0.84 |
| np_shots | 0.65 | 0.84 |
| interceptions | 0.61 | 0.83 |
| key_passes | 0.59 | 0.81 |
| npxg | 0.52 | 0.74 |
| xa | 0.37 | 0.62 |
| np_goals | 0.23 | 0.38 |
| assists | 0.13 | 0.28 |

**Football interpretation:** frequent actions (passes, tackles, shots) describe a player reliably after a few hundred minutes. **Goals and assists per 90 remain mostly noise even over a full season**, while npxG and xA carry far more signal. This is the quantitative reason to judge finishers by npxG and creators by xA, not by goals and assists. It also explains why the 900-minute threshold matters more for some metrics than others: Pastore (909 min) keeps 2nd place in progressive passes after regression, because that metric is reliable at his sample size.

---

# Phase 5 — Player profile

Status: implemented (decision D018).

## Questions the profile answers, in reading order

1. **Who and where?** Name, club(s), league, season. The season is shown prominently: the data is historical (2015/16), not current form.
2. **How much did he play, and can we trust the numbers?** Minutes, appearances, starts, primary position and its share of his minutes. An explicit note appears when he is below the 900-minute threshold and therefore not ranked.
3. **What kind of player is he compared with his position peers?** Percentiles grouped by theme, using a template for each position group (below).
4. **In what context?** Team possession next to defensive metrics (D017), the reference population (size, seasons, threshold), and the data source.

The profile deliberately shows **no overall rating**: a single score would need a weighting of metrics that the project has not justified (CLAUDE.md, "Do not invent methodologies").

## Position templates

Each position group shows the metrics that matter most for its role. Other metrics remain available in the full table.

| Theme | Striker | Att. mid / winger | Central mid | Full-back | Centre-back | Goalkeeper |
|---|---|---|---|---|---|---|
| Shooting | npxG, np shots, npxG/shot, np goals | npxG, np shots, np goals | npxG | | | |
| Creation | xA, key passes, passes into box | xA, key passes, passes into box, assists | xA, key passes | xA, key passes | | |
| Progression | progressive carries | progressive passes, progressive carries, final-third passes | progressive passes, progressive carries, final-third passes, pass completion | progressive passes, progressive carries, final-third passes | progressive passes, pass completion | long-pass share, pass completion |
| Defending | pressures | pressures, tackles | tackles, interceptions, ball recoveries, pressures | tackles, interceptions, pressures | interceptions, tackles, ball recoveries | |
| Aerial | aerials won, aerial win % | | | aerial win % | aerials won, aerial win % | |
| Goalkeeping | | | | | | save %, shots on target faced, claims, sweeper actions |

## How each value is displayed

| Element | Rule |
|---|---|
| Value | per 90 for counts, raw for ratios, with the season total |
| Percentile | 0–100 within the reference population. **Not shown** (with a reason) when the player is below the minutes threshold or a ratio has too few attempts |
| Reliability | from the regressed-estimate weight *w* (Phase 4.1 §4): **high** w ≥ 0.8, **medium** 0.5 ≤ w < 0.8, **low** w < 0.5. These bands are a display convention, chosen so that "low" means the observed value carries less than half signal |
| Regressed estimate | shown next to the value for count metrics ("expected underlying rate") |
| Unavailable | metrics unavailable from the source (capability) are shown as unavailable, never as 0 |

## Data source

Every profile states "Data: StatsBomb Open Data (2015/16)". Before any public deployment, the official StatsBomb logo from their media pack must be added (User Agreement §1.4). The API serves derived, aggregated metrics only (D004).

---

# Phase 6 — Player comparison

Status: implemented (decision D019).

## Football question

> "Among these 2–4 candidates for a role, how do their profiles differ, and **which differences are large enough to be real rather than noise**?"

A comparison view naturally invites "who is better?". The view must therefore show *where* players differ and how confident we can be. It must not produce a ranking.

## Rules

| Rule | Why |
|---|---|
| 2 to 4 player-seasons | beyond 4, a grouped chart becomes unreadable and colours stop being distinguishable |
| Metrics shown: the position template of the first player's group, plus the templates of the other groups if they differ | the scout chooses the role being evaluated |
| **Same position group**: percentiles compared directly | same reference population |
| **Different position groups**: allowed, with a warning. Each percentile stays relative to its own group, so per-90 values are the comparable figures | a winger at the 80th percentile among wingers and a striker at the 80th among strikers are not "equal" |
| Different leagues | allowed. The population pools the four leagues of the same season, and league strength is not adjusted (stated in the view) |
| Different minutes | each player shows minutes and reliability; uncertainty is part of the difference test (below) |
| No radar chart | radar area depends on axis order and exaggerates differences (area grows with the square of the values). Grouped bars on a common 0–100 scale are used instead |

## Is a difference real? (count metrics)

Each count metric has a regressed estimate *r* (Phase 4.1 §4) and, under the same normal–normal model, a **posterior standard deviation**:

```
sd = √(w × noise_per_90 / exposure)        (per-90 units)
```

For two players A and B, the difference is called **clear** when

```
|r_A − r_B| > 1.96 × √(sd_A² + sd_B²)
```

This is the usual 95 % threshold for a difference between two independent estimates. Otherwise the view says **"within noise"**.

With 3–4 players, the view states, per metric, whether the **leader is clearly ahead of the second** (same test between the top two regressed estimates). This answers the scout's question "is the best one really better on this?" without ranking everybody.

Ratios (pass completion, save %) have no posterior SD in v1. Their differences are shown without a test, and only when both ratios are reliable (minimum attempts, Phase 4.1 §1).

**Validation** (`scripts/validation/phase6_validation.py`): using first-half-season data only, pairs of players in the same position group are classified "clear" or "within noise" for each metric. Then we check how often the sign of the difference holds in the second half. A useful rule must show a much higher persistence for "clear" differences than for "within noise" ones.

**Limitations:** the test assumes the model of Phase 4.1 (position-group prior, no league or team adjustment). It reflects sampling noise only, not differences in team context or role.

## Validation of the difference rule (2026-10-05)

Reproduce: `.venv/bin/python scripts/validation/phase6_validation.py`. 977 players with ≥ 450 minutes in each half-season. All pairs within the same position group. The verdict uses first-half data, and persistence = same sign of the difference in the second half.

| Metric | Pairs | Judged clear | Persists if clear | Persists if within noise |
|---|---:|---:|---:|---:|
| npxg | 84,304 | 10 % | **88 %** | 64 % |
| xa | 84,955 | 9 % | **89 %** | 61 % |
| key_passes | 84,955 | 16 % | **93 %** | 64 % |
| progressive_passes | 87,078 | 38 % | **92 %** | 67 % |
| tackles | 84,663 | 20 % | **91 %** | 67 % |
| interceptions | 84,565 | 24 % | 73 % | 56 % |
| np_goals | 59,748 | 2 % | 94 % | 56 % |
| assists | 58,301 | 1 % | 77 % | 57 % |

**Reading:** a difference flagged "clear" keeps its direction about 9 times out of 10. A "within noise" difference is barely better than a coin toss (50 %). The rule therefore separates real differences from noise.

**Football interpretation:**
- **Interceptions** persist less (73 %): they depend on match context (opponent, score, team style), which changes between the two halves. Treat interception differences with extra caution.
- **Goals**: over half a season, only **2 %** of player pairs can be told apart, against 38 % for progressive passes. Goals are a poor criterion for separating two players. Prefer npxG and shot volume.
- Full-season comparisons have smaller standard deviations than half-seasons, so more pairs are "clear" in the application than in this test.

---

# Phase 7 — Scouting

Status: implemented (decision D020).

## Football question

> "In a position group, which players match the profile I am looking for, and how do I order the candidates **without inventing weights**?"

A weighted score (e.g. 40 % tackles + 30 % interceptions + 30 % recoveries) needs weights that the data cannot justify. Two scouts would produce two rankings, neither more "correct". CLAUDE.md forbids undocumented scoring systems. The scouting tool therefore uses **filters plus dominance**, and no composite score.

## 1. Screening (filters)

- Population: one position group, eligible players (≥ 900 minutes), complete seasons. Percentiles are the ones of the profile (same reference population).
- Criteria: "metric ≥ X-th percentile" (1–6 criteria). For ratios, a player whose ratio is not reliable (too few attempts, Phase 4.1 §1) **does not pass** the criterion: the requirement cannot be verified.
- Context filters: competition, team possession range (e.g. to find ball-winners in high-possession teams, where defensive volume is not inflated by having little of the ball, D017).

## 2. Ordering without weights

**Pareto tiers.** Candidate A *dominates* B when A's percentile is at least B's on every criterion and strictly higher on at least one. Tier 1 = candidates dominated by nobody. Tier 2 = candidates dominated only by tier-1 players, and so on (non-dominated sorting).

- Football reading: a tier-1 player is one for whom **no other candidate is better on everything you asked for**. Two tier-1 players are better on different criteria, and choosing between them is a scouting judgement, not a calculation.

**Within a tier: weakest criterion (maximin).** Candidates are sorted by their *lowest* criterion percentile, highest first. This is a standard decision rule ("no weak point first") that needs no weights. Ties are broken by minutes played, so larger samples come first.

## 3. Role presets

Presets pre-fill criteria for common roles. They are **editable starting points, not models**. Thresholds are round conventional cut-offs (60th, 70th, 75th, 80th percentile).

| Preset | Group | Criteria (min percentile) | Football intent |
|---|---|---|---|
| Ball-winning midfielder | central midfield | tackles 70, interceptions 60, ball recoveries 60 | wins the ball back |
| Deep-lying playmaker | central midfield | progressive passes 80, passes into final third 70, pass completion 60 | moves the ball forward from deep |
| Creative winger / AM | attacking mid / winger | xA 75, key passes 70, progressive carries 60 | creates chances and carries the ball |
| Goal-threat striker | striker | npxG 75, np shots 70 | gets into scoring positions |
| Pressing forward | striker | pressures 75, npxG 50 | defends from the front while still threatening |
| Attacking full-back | full-back | passes into final third 70, xA 60, progressive carries 60 | contributes in the final third |
| Ball-playing centre-back | centre-back | progressive passes 75, pass completion 60, aerial win % 50 | progresses play while defending |
| Sweeper keeper | goalkeeper | sweeper actions 70, pass completion 50 | defends space behind the line, takes part in build-up |

## 4. Near misses

Players who fail **exactly one** criterion by at most *t* percentile points (default 5, user-adjustable) are listed separately, with the missed criterion and the gap. Thresholds are noisy (see validation): a player at the 68th percentile is not meaningfully different from one at the 70th.

## Limitations

- Percentiles are observed values: a candidate near a threshold may pass or fail by chance. Reliability is shown, near misses are listed, and shortlist stability is measured (below).
- Dominance treats every criterion as equally relevant, but chooses no trade-off between them.
- No age, contract or market value (not in the data). This is a *performance* screen, not a full recruitment process.

## Validation of scouting (2026-10-05)

Reproduce: `cd scripts/validation && ../../.venv/bin/python phase7_validation.py`. For each preset, shortlists and near misses are built on first-half-season data and followed in the second half.

| Preset | Shortlist | Still pass every criterion | Mean criterion pct later | Near misses | Mean pct later |
|---|---:|---:|---:|---:|---:|
| Ball-winning midfielder | 21 | 14 % | 70 | 5 | 68 |
| Deep-lying playmaker | 16 | 69 % | 86 | 5 | 80 |
| Creative winger / AM | 24 | 33 % | 76 | 5 | 69 |
| Goal-threat striker | 23 | 48 % | 73 | 3 | 69 |
| Pressing forward | 9 | 22 % | 60 | 5 | 56 |
| Attacking full-back | 18 | 33 % | 75 | 6 | 70 |
| Ball-playing centre-back | 13 | 46 % | 78 | 1 | 71 |
| Sweeper keeper | 13 | 38 % | 68 | 1 | 30 |

(Mean criterion percentile: 50 = an average player of the group.)

**Findings:**

1. **Hard thresholds are brittle.** Only 14–69 % of shortlisted players meet every threshold again in the next half-season. Requiring *all* criteria multiplies the chances of failing one by noise. The ball-winning preset is the most fragile, consistent with defensive actions being context-dependent (Phase 6).
2. **The selection itself is sound.** Shortlisted players stay well above average later on (70th–86th percentile on the criteria, 60th for the pressing forward).
3. **Near misses perform almost as well** (68th–80th percentile; the goalkeeper row has a single player and is not interpretable). Listing them is justified.
4. **Screening on regressed estimates did not help.** Same shortlists and outcomes: among players above 900 minutes, regression barely changes the order. So observed percentiles are kept, for transparency.

**Consequence for use:** a shortlist is a starting point for video and live scouting, not a decision. The interface states this next to the results.

---

# Phase 8 — Team analysis

Status: implemented (decision D021).

## Football questions

1. **Did the team get the results its performances deserved?** Points against expected points; goal difference against non-penalty xG difference.
2. **How does it play?** Possession, pressing intensity, directness, counter-attacking, set-piece reliance, chance quality.
3. **How does it compare?** Every team-season against the other 80 of the D011 slice.

Unit: team × competition-season, from canonical events (shoot-outs excluded). Season values are **ratios of season totals**, not averages of match ratios, so long and short matches are weighted correctly.

## Results versus performance

| Metric | Definition | Limitations |
|---|---|---|
| `points_per_match` | 3 win / 1 draw / 0 loss | |
| `goal_diff_per_match` | (goals for − goals against) / matches, own goals included | |
| `npxg_for`, `npxg_against` (per match) | StatsBomb xG of non-penalty shots | provider model (D007); capability-gated |
| `npxg_diff_per_match` | npxG for − npxG against | |
| `xpts_per_match` | expected points (below) | |

**Expected points (xPts).** Each shot is treated as an independent chance to score with probability = its xG (penalties included). A team's goal count then follows a Poisson-binomial distribution, computed exactly by convolution over its shots. From both teams' distributions:

```
P(win)  = Σ_{i>j} P_team(i) · P_opp(j)
P(draw) = Σ_i     P_team(i) · P_opp(i)
xPts    = 3 · P(win) + P(draw)
```

Limitations: shots in the same attack (rebounds) are not independent, so variance is overstated for rebound sequences. Own goals carry no xG and are ignored. Game state is not modelled (a team leading 2–0 may shoot less).

## Style

| Metric | Definition | Football reading | Limitations |
|---|---|---|---|
| `possession_pct` | share of passes attempted (D017 proxy) | how much the team has the ball | pass share, not time |
| `ppda` | opponent passes in their own 60 % of the pitch ÷ own defensive actions (tackles, interceptions, fouls committed) in the opponent's 60 % | **passes allowed per defensive action**: lower = more intense, higher pressing | standard public definition (Trainor); depends on what counts as a defensive action per provider |
| `long_pass_share` | passes ≥ 40 m / passes attempted | directness of build-up | length on the standard pitch (D005) |
| `progressive_pass_share` | progressive passes / completed open-play passes | how often a pass moves the ball significantly forward | Wyscout-style definition (Phase 4) |
| `crosses_per_match` | open-play crosses attempted per match | wide, crossing play | |
| `counter_npxg_share` | share of npxG from possessions starting as counter-attacks | reliance on transitions | **StatsBomb play pattern** ("From Counter"): capability-gated (`has_possession_ids`) |
| `set_piece_npxg_share` | share of npxG from possessions starting from corners or free kicks (throw-ins excluded, see validation) | reliance on set pieces | StatsBomb possession origin; free-kick possessions include restarts that turn into open play |
| `npxg_per_shot_for`, `npxg_per_shot_against` | npxG / non-penalty shots | chance quality created / conceded | |

Percentiles: each team-season **within its own league-season** (20 teams). Pooling the four leagues was rejected after validation (league norms differ, see below). Like player percentiles, they are **descriptive**: a high PPDA is not "bad", it describes a deeper defensive block.

## Validation

1. **Do underlying numbers predict the future better than results?** Using the first half of each season, correlate {points, goal difference, npxG difference, xPts} per match with points per match in the second half. If npxG difference predicts better than past points or goal difference, team analysis should lead with it.
2. **Face validity of styles**: 2015/16 is well documented (e.g. Leicester's low-possession counter-attacking title, Barcelona's possession, pressing sides).

## Validation of team metrics (2026-10-05)

Reproduce: `cd scripts/validation && ../../.venv/bin/python phase8_validation.py`.

### Predicting second-half points (80 team-seasons, first-half measures)

| First-half measure | r with second-half points per match | R² |
|---|---:|---:|
| Points per match | 0.62 | 0.39 |
| Goal difference per match | 0.65 | 0.43 |
| Expected points per match | 0.70 | 0.48 |
| npxG difference per match | **0.70** | **0.49** |

Underlying performance (npxG difference, xPts) predicts future results better than past points or goal difference. This reproduces the classic analytics finding, but with 80 teams the margin is modest (R² 0.49 vs 0.39). The team view therefore leads with points *and* expected points, never one alone.

### Corrections made during validation

1. **Set pieces**: counting throw-in possessions gave implausible shares (up to 65 % of npxG). Throw-ins were removed. Shares are now 25–49 %, and the most set-piece reliant include Pulis's West Bromwich Albion.
2. **League effect on PPDA**: mean PPDA was 13.0 in La Liga against 15.5 in the Premier League and Ligue 1 (La Liga also has more fouls per match, and fouls count as defensive actions). With pooled percentiles, the five "most intense pressing" teams were all Spanish. **Percentiles are now computed within each league.** Within-league pressing leaders are Manchester United, Liverpool and Tottenham (Premier League), Celta Vigo, Barcelona and Rayo Vallecano (La Liga), and PSG and Lyon (Ligue 1).

### Face validity (2015/16)

- Possession: Barcelona, PSG and Napoli are highest.
- Counter-attack reliance: Leicester City is in the top 5.
- Points above expected: Atlético Madrid, Real Madrid and Leicester City (+14.8 points over the season). Below expected: Toulouse, Aston Villa and Hellas Verona.
- Leicester City: 81 points (the official total). Possession at the 15th percentile of the league, long passes at the 90th, counter-attack share at the 95th, chance quality per shot at the 100th. This is the documented profile of that title season.

---

# Phase 9a — Player similarity

Status: implemented (decision D022).

## Football question

> "Which players had a statistical profile most like player X, in the same role?"

The typical use is replacing a departing player, or finding a cheaper version of a target. The answer describes **how a player played** (his statistical style and volume). It does not say how good he is, and it does not judge suitability for another team.

## Method (required elements, CLAUDE.md "Player similarity")

| Element | Choice | Reason |
|---|---|---|
| Population | eligible players (≥ 900 min) of the **same position group**, complete seasons, four leagues pooled | comparable roles; same reference population as percentiles |
| Variables | the count metrics of the position template (Phase 5), as **regressed per-90 estimates** | the role's relevant actions. Regressed values keep sampling noise from looking like style (Phase 4.1). Ratios are excluded in v1: they are unreliable for low volumes |
| Normalisation | z-score within the position group | each metric counts on the same scale, whatever its unit |
| Weighting | none chosen by hand (see distance) | no unjustified weights |
| Distance | **selected by validation** among four candidates (below) | |
| Displayed similarity | **similarity percentile**: share of the group that is *farther* from the target than this candidate ("closer than 97 % of central midfielders") | interpretable and population-based, no arbitrary "% similar" |
| Explanation | per-metric z-scores of target and candidate, with the largest differences listed | the scout sees *where* players match or differ |

### Choosing the distance: the fingerprint test

A similarity method is useful only if it recognises **the same player** across two independent samples. For each position group, players with ≥ 450 minutes in each half-season get a first-half profile and a second-half profile. For every second-half profile, all first-half profiles are ranked by distance, and we record where the same player's first-half profile lands.

Candidates:

1. Euclidean distance on z-scores of **observed** per-90 values;
2. Euclidean distance on z-scores of **regressed** per-90 values;
3. **Mahalanobis** distance on regressed values (corrects for correlated metrics, e.g. tackles and interceptions both measuring defensive volume);
4. **Cosine** distance on regressed z-scores (shape of the profile, ignoring overall volume).

Selection criterion: highest top-1 and top-5 self-retrieval rates, and lowest median self-rank. A random method would rank a player's own profile first with probability 1/N.

## Limitations

- Statistical similarity is not quality-adjusted: a player at the same "shape" but lower volume ranks lower (except with cosine distance).
- Team context (possession, tactics) shapes a player's numbers. Two similar profiles may reflect similar team roles rather than similar players.
- One season, no age, no physical data.
- Positions are formation slots: the template defines the role (Phase 5 limitation).

## Validation of similarity (2026-10-05)

Reproduce: `cd scripts/validation && ../../.venv/bin/python phase9_similarity_validation.py`. Fingerprint test on 903 players (≥ 450 min in each half; centre-backs, full-backs, central midfielders, attacking midfielders/wingers, strikers. Goalkeepers have only 2 template count metrics and are excluded).

| Method | Same player ranked 1st | Top 5 | Top 10 % | Median rank |
|---|---:|---:|---:|---:|
| Random | 0.6 % | 2.8 % | 10 % | ~92 |
| Euclidean, observed per 90 | 15.1 % | 34.1 % | 59.6 % | 12 |
| **Euclidean, regressed per 90 (selected)** | 14.6 % | 34.0 % | 59.6 % | 12 |
| Mahalanobis, regressed | 11.4 % | 30.5 % | 53.6 % | 17 |
| Cosine, regressed | 14.5 % | 35.8 % | 62.3 % | 12 |

**Reading:**

- A statistical profile is a real but noisy fingerprint. A player's other half-season is found about 25 times more often than chance, but it is the single nearest profile only 15 % of the time. **Similarity lists are neighbourhoods**, and the UI says so.
- Mahalanobis performs worse. Inverting the covariance over-weights rare directions, which are mostly noise in one season of data. Rejected.
- Euclidean and cosine are statistically tied (gaps of about 1–2 points, with a standard error of about 1.6). **Euclidean on regressed values** is selected because it keeps volume (a scout replacing a high-volume player cares about volume) and regressed values protect low-minute targets.

**Face validity** (full season): Kanté → Idrissa Gueye, Augusto Fernández, Kirchhoff, Illarramendi, Tioté, Casemiro. Fàbregas → Verratti, Jorginho, Kroos. Vardy → Fernando Torres, Diego Costa, Lukaku. Marcelo → Florenzi, Mendy, Alex Telles, Alex Sandro.

---

# Phase 9b — Shot zone maps

Status: implemented (decision D023).

## Football questions

- **Player:** where does he shoot from, and how good are those chances? (A poacher in the six-yard box is a different profile from a long-range shooter with the same shot volume.)
- **Team:** where does it create, and where does it concede?

## Why zones, not individual shots

1. **Licensing (D004):** an API returning every shot's position is event-level data. Zones are aggregates.
2. **Robustness:** a season shot map of about 80 dots invites over-reading single shots. Zone totals with xG per shot are easier to interpret correctly.

Individual-shot maps may later be produced as local static images for publication with attribution (allowed as "published analysis"), never served by the API.

## Zones

Canonical metres, attacking towards x = 105, goal centre y = 34. Box dimensions are from the Laws of the Game; the 25 m "edge of the box" line is a common analytics convention.

| Zone | Definition | Typical chance |
|---|---|---|
| Six-yard box | x ≥ 99.5 and \|y − 34\| ≤ 9.16 | very high |
| Box, central | in the penalty area, \|y − 34\| ≤ 9.16, outside the six-yard box | high |
| Box, wide | in the penalty area, 9.16 < \|y − 34\| ≤ 20.16 | medium, tight angle |
| Edge of the box | 80 ≤ x < 88.5 and \|y − 34\| ≤ 20.16 | low |
| Outside, wide | x ≥ 80 and \|y − 34\| > 20.16 | very low |
| Long range | x < 80 | very low |

Penalties are excluded from zones and reported separately. Shoot-outs are excluded.

## Displayed per zone

Shots, goals, npxG, npxG per shot, and the **share of the player's shots** in the zone next to the **position group's share** (eligible players, same population as percentiles). For teams: shots for and against, with the league average share.

## Validation

1. **Conservation:** zone totals equal the season's non-penalty shots, goals and npxG.
2. **Sanity of zones:** npxG per shot must fall from the six-yard box to long range. A violation would reveal a coordinate or zone error.

## Validation of shot zones (2026-10-05)

Reproduce: `.venv/bin/python scripts/validation/phase9_shot_zones_validation.py` (all 37,488 non-penalty shots of the D011 slice).

| Zone | Shots | Share | Goals | Conversion | npxG per shot |
|---|---:|---:|---:|---:|---:|
| Six-yard box | 2,905 | 7.7 % | 822 | 28.3 % | 0.276 |
| Box, central | 13,123 | 35.0 % | 1,899 | 14.5 % | 0.137 |
| Box, wide | 6,597 | 17.6 % | 370 | 5.6 % | 0.053 |
| Edge of the box | 10,838 | 28.9 % | 409 | 3.8 % | 0.038 |
| Outside, wide | 175 | 0.5 % | 15 | 8.6 % | 0.008 |
| Long range | 3,850 | 10.3 % | 54 | 1.4 % | 0.017 |

- **Sanity:** npxG per shot falls monotonically from the six-yard box to long range.
- **Conservation:** zone totals equal all non-penalty shots (37,488) and npxG (3,433.44).
- **Calibration of the provider's xG:** in every large zone, the real conversion rate is close to the mean xG (28.3 % vs 0.276; 14.5 % vs 0.137; 3.8 % vs 0.038). This is an independent check that StatsBomb xG is well calibrated on this data.
- **Anomaly:** wide shots outside the box convert at 8.6 % against 0.8 % expected. This is a tiny sample (175 shots), plausibly crosses that ended in the net, so no conclusion is drawn.

**Face validity:** Vardy takes 27 % of his shots from the wide part of the box (strikers: 19 %), consistent with his runs into the channels. Messi takes 43 % from the central box (attacking midfielders and wingers: 29 %). Goal totals match the record: Vardy 19 non-penalty goals + 5 penalties = 24, Messi 23 + 3 = 26.

---

# Phase 11.1 — Expected Threat (xT)

Status: implemented (decision D025).

## Football question

> "Who moves the ball into dangerous areas, even when no shot follows?"

Assists and key passes credit only the last action before a shot. A midfielder who breaks lines with the pass *before* the key pass, or carries the ball 30 m into the box, gets no credit. **Expected Threat** values every pass and carry by how much it increases the probability that the team scores soon.

## Method (Karun Singh, 2018, public)

The pitch is divided into a **16 × 12 grid** (cells of 6.6 × 5.7 m on the canonical pitch). Each cell *z* has a threat value:

```
xT(z) = s(z) · g(z)  +  m(z) · Σ_z' T(z → z') · xT(z')
```

| Term | Meaning | Estimated from |
|---|---|---|
| s(z) | probability that the player in *z* shoots | open-play shots / (shots + moves) in *z* |
| g(z) | probability that a shot from *z* is a goal | **mean StatsBomb xG** of open-play shots from *z* (smoother than goal counts in sparse cells; StatsBomb xG was shown to be well calibrated in Phase 9b) |
| m(z) | probability that the player moves the ball instead | moves / (shots + moves) in *z* |
| T(z → z') | probability that a move from *z* successfully reaches *z'* | successful moves *z → z'* / all moves from *z*. Failed moves end the possession and carry no value |

The equation is solved by iteration from xT = 0 until the largest change is below 10⁻⁶ (value iteration).

**Value of an action:** for a *successful* open-play pass or carry, `xT(end cell) − xT(start cell)`. A backward pass is therefore negative. Failed passes are valued 0 in v1 (the original formulation), which is a known limitation (see below).

**Player metrics:** `xt_pass` and `xt_carry` (season sums of net xT added, per 90 in profiles), regressed like other counts (Phase 4.1).

## Scope and choices

- **Open play only:** actions with a set piece (corner, free kick, throw-in, goal kick, kick-off) are excluded from both the model and the valuation. Set pieces are analysed separately (Phase 11.6).
- **Carries** are capability-gated (`has_carries`). With a provider without carries, xT is computed from passes only, and `xt_carry` is unavailable.
- The model is fitted on all complete seasons of the population. The predictive validation below fits it on first-half data only.

## Limitations

- **Failed actions are not penalised**: a player who attempts many risky passes and loses the ball is not charged for it in v1.
- **Location-only:** xT ignores defensive pressure, game state and the identity of the receiver.
- **Grid resolution:** 16 × 12 cells is the standard compromise. Finer grids are sparse, coarser ones blur the box.
- **Model output:** xT depends on the StatsBomb xG used for g(z), so it is valid within StatsBomb data (D007).

## Validation

1. **Sanity:** xT must rise towards the opponent's goal and be roughly symmetric left/right.
2. **Predictive value:** fitted on first-half data only, players' first-half xT per 90 should predict their second-half **npxG + xA per 90** (their direct goal threat) at least as well as first-half key passes do. Otherwise xT adds noise, not information.

### Results (2026-10-08)

Reproduce: `cd scripts/validation && ../../.venv/bin/python phase11_xt_validation.py`.

**1. Surface:** fitted on 2,462,944 open-play actions (52 iterations). Mean threat rises from 0.003 near the own goal to 0.075 in the last column, with a maximum of 0.276 in front of goal (consistent with six-yard-box xG). Left/right asymmetry: 0.0005.

**2. Pre-registered criterion: FAILED.** First-half xT per 90 correlates only r = 0.29 with second-half npxG + xA per 90 (key passes 0.54, xA 0.57), and adds nothing beyond first-half npxG + xA (R² 0.688 → 0.689). Interpretation: xT measures **ball progression, whose value is mostly realised by teammates**. A deep playmaker moves the ball into dangerous zones but rarely shoots or plays the final pass. The criterion tested xT against the wrong outcome, and the failure is kept on record rather than replaced silently.

**3. What xT claims to measure: VALIDATED.**

| Test | Result |
|---|---|
| Player stability, first half → second half per 90 | **r = 0.80** (progressive passes 0.82, key passes 0.81): a repeatable player trait |
| Team xT vs team npxG, same matches (80 team-seasons) | **r = 0.91**: progression measured by xT turns into chances |
| Team first-half xT → second-half npxG | r = 0.72 (first-half npxG itself: 0.75; adding xT: R² +0.011) |

**Conclusion:** xT is used and presented as a **measure of contribution to ball progression and chance creation upstream of the shot**, not as a predictor of a player's own goals and assists.

**Effect on similarity (Phase 9a):** adding xT to the templates slightly improves the fingerprint test (Euclidean regressed: top-5 34.0 % → 35.9 %, top-10 % 59.6 % → 62.6 %).

**Face validity** (2015/16, ≥ 900 min): xT from passes, central midfielders: James Rodríguez, Barrada, Pastore, Fàbregas, Milner. xT from carries, attacking midfielders and wingers: Neymar, Keita Baldé, Mertens, Messi. Full-backs: Alex Sandro, Carvajal, Maicon, Dani Alves, Mendy. Centre-backs: Mascherano, Maksimović, Juan Jesus, Blind.

---

# Phase 11.2 — Touch, reception and progression zone maps

Status: implemented (decision D026).

## Football questions

- **Touches:** where is the player involved with the ball?
- **Receptions:** where does he receive passes? (A false nine dropping deep and a striker on the last line have different maps.)
- **Progression:** where do his progressive passes and carries take the ball?

## Zones

**6 strips** along the pitch (17.5 m each) × **5 channels** across it: right wing, right half-space, centre, left half-space, left wing. Channel edges are the pitch markings: penalty-box lines (y = 13.84 and 54.16) and six-yard-box lines (y = 24.84 and 43.16). This is the wings / half-spaces / centre frame used in coaching. Canonical y = 68 is the attacking team's **left** (docs/ARCHITECTURE.md §4.2).

| Map | Events (provider-independent) |
|---|---|
| Touches | the player's passes, shots, take-ons, ball recoveries, interceptions, clearances, miscontrols and dispossessions (start location). Carries and ball receipts are excluded because they are StatsBomb-specific |
| Receptions | **completed passes whose recipient is the player** (end location). This uses the pass recipient field, available from most providers, rather than StatsBomb "ball receipt" events |
| Progression | end locations of the player's progressive actions: completed open-play passes and carries meeting the Phase 4 progressive definition (carries capability-gated) |

Each zone shows the player's **share** of the map's actions, and the **position group's share** (all eligible players of the group pooled). The view offers two encodings: share (single hue, opacity = magnitude) and difference from the group (diverging blue/red). The API returns zone aggregates only (D004).

## Validation

- **Orientation:** Marcelo (left-back) has 72 % of his touches and 77 % of his receptions in the left-wing channel, and 0 % on the right. This check exposed a mirrored left/right drawing in the shot map (invisible there because its zones are symmetric), which was fixed.
- **Football reading:** Marcelo's progressive actions end mostly in the left half-space (43 %) rather than on the wing (37 %): he moves inside with the ball, a known trait of his game.

## Limitations

- Shares hide volume: the action count is shown with each map.
- The group baseline pools players, so high-volume players weigh more.
- One season, all game states mixed.
