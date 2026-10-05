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
