# StatsBomb → Canonical Mapping Specification

Phase 1B deliverable (2026-10-04). **Implemented in Phase 2** (`src/football_platform/providers/statsbomb/`), with tests in `tests/providers/statsbomb/`.

Inputs: [STATSBOMB_DATA_DICTIONARY.md](STATSBOMB_DATA_DICTIONARY.md). Target: canonical model v1.1 in [ARCHITECTURE.md](../ARCHITECTURE.md).

Rules applied throughout:

- Nothing is silently dropped. Unmapped event types become `other` and keep `provider_event_type`.
- An absent StatsBomb boolean flag maps to `False` (StatsBomb omits false flags). An absent *value* maps to `None` (unknown).
- Every mapping decision with a football consequence is listed here and covered by a test in Phase 2.

---

## 1. Identity

| Canonical | StatsBomb source |
|---|---|
| Competition | `competition_id` (+ name, gender, `competition_international`) |
| Season | `(competition_id, season_id)`. **Note:** StatsBomb `season_id` is shared across competitions (27 = 2015/16 everywhere), so it is only unique *with* the competition |
| Team | `team_id`. National and club teams share the id space. `team_type` comes from `competition_international` |
| Player | `player_id`. `name` ← `player_name`, `known_name` ← `player_nickname` |
| Match | `match_id` |
| Event | `id` (UUID) |

All are stored as `ExternalId(provider="statsbomb_open", …)` (D006).

## 2. Coordinates (D005)

```
x_m = x / 120 * 105
y_m = (80 - y) / 80 * 68      # StatsBomb y grows downwards; canonical y grows upwards
```

Orientation needs no change (StatsBomb already orients every team left→right). Applies to `location` and all `end_location` fields. Shot `end_location[2]` (height) is kept as `end_z` in StatsBomb units, because the goal frame is the same size everywhere.

Test cases (Phase 2): (0,0) → (0,68); (120,80) → (105,0); (60,40) → (52.5,34); the penalty spot (108,40) → (94.5,34).

## 3. Event types

| StatsBomb type | Canonical type | Outcome rule | Notes |
|---|---|---|---|
| Pass | `pass` | `outcome` absent → success; Incomplete/Out/Pass Offside → fail; Unknown → unknown; **Injury Clearance → `other` outcome `not_applicable`** (deliberate ball-out, excluded from pass completion) | `set_piece` ← `pass.type` (Throw-in, Free Kick, Corner, Goal Kick, Kick Off); Recovery/Interception types → open play |
| Ball Receipt* | `ball_receipt` *(capability-gated)* | absent → success; Incomplete → fail | |
| Carry | `carry` *(capability-gated)* | not_applicable | a carry has no success/failure in the source |
| Pressure | `pressure` *(capability-gated)* | not_applicable | `counterpress` flag kept |
| Dribble | `take_on` | Complete → success, Incomplete → fail | |
| Dribbled Past | `dribbled_past` | fail (from the defender's perspective) | |
| Duel / Tackle | `duel` (kind `ground`) | Won, Success In Play, Success Out → success; Lost In Play, Lost Out → fail | |
| Duel / Aerial Lost | `duel` (kind `aerial`) | fail | |
| `aerial_won` flag on Pass/Clearance/Shot/Miscontrol | attribute `aerial_won = True` on that event | – | **Not** turned into a separate event. Aerial duels won = count of `aerial_won` flags |
| 50/50 | `duel` (kind `loose_ball`) | per `50_50.outcome` | |
| Interception | `interception` | Won, Success In Play, Success Out → success; Lost In Play, Lost Out → fail | |
| Clearance | `clearance` | success | |
| Block | `block` | success | `save_block` kept |
| Ball Recovery | `ball_recovery` | `recovery_failure` → fail, else success | |
| Miscontrol | `miscontrol` | fail | |
| Dispossessed | `dispossessed` | fail | |
| Shot | `shot` | Goal → success, others → fail | `shot_outcome` kept in detail. `set_piece` ← `shot.type` (Penalty, Free Kick, Corner) |
| Own Goal Against | `own_goal` | – | credited to the conceding player. Score check must include own goals |
| Own Goal For | `other` | – | mirror of Own Goal Against for the benefiting team. Kept for traceability, **never counted** in scores or stats |
| Goal Keeper | `goalkeeper_action` | from `goalkeeper.outcome` | `gk_action_kind` ← type (shot_faced, save, goal_conceded, claim, punch, sweeper, …) |
| Foul Committed | `foul_committed` | – | card → also emits `card` |
| Foul Won | `foul_won` | – | |
| Bad Behaviour | `card` | – | |
| Substitution | `substitution` | – | `replacement` → player on |
| Half Start / Half End | `period_start` / `period_end` | – | one per team. Keep one per period |
| Starting XI, Tactical Shift | not events in canonical form | – | consumed into Appearance / formation data |
| Offside, Shield, Error, Injury Stoppage, Referee Ball-Drop, Player On/Off | `other` | – | `provider_event_type` preserved |

No StatsBomb event is dropped.

## 4. Event attributes

| Canonical | StatsBomb |
|---|---|
| `period` | `period` |
| `time_s` | `timestamp` (since period start) → seconds |
| `set_piece` (action restarts play) | `pass.type` / `shot.type` |
| `possession_origin` *(optional)* | `play_pattern` (possession-level) |
| `possession_id` *(optional)* | `possession` |
| `body_part` | Right Foot → foot_right, Left Foot → foot_left, Head → head, Keeper Arm / hands → hands, Drop Kick → other (kicked, foot side not recorded), other → other |
| `under_pressure` *(optional)* | `under_pressure` (absent → False) |
| `related_event_ids` | `related_events` |
| `provider_metrics` | `shot.statsbomb_xg` → `("xg", value, "statsbomb_open", "statsbomb_xg")` |
| pass detail | `recipient`, `is_cross`, `is_switch`, `is_cut_back`, `is_through_ball` (`through_ball` flag or technique Through Ball), `height`, `assisted_shot_id`, `is_shot_assist`, `is_goal_assist` |
| shot detail | `shot_outcome`, `technique`, `is_first_time`, `key_pass_id`, `shot_freeze_frame` (optional) |

## 5. Positions

Canonical position = **(line, role, side)**, provider-independent. Wyscout v2 only has the line level, which is why the levels are separate.

| StatsBomb position | line | role | side |
|---|---|---|---|
| Goalkeeper | GK | GK | C |
| Right / Left Back | DEF | FB | R / L |
| Right / Left / – Center Back | DEF | CB | R / L / C |
| Right / Left Wing Back | DEF | WB | R / L |
| Right / Left / Center Defensive Midfield | MID | DM | R / L / C |
| Right / Left / – Center Midfield ("Right Center Midfield"…) | MID | CM | R / L / C |
| Right / Left Midfield | MID | WM | R / L |
| Right / Left / Center Attacking Midfield | MID | AM | R / L / C |
| Right / Left Wing | FWD | W | R / L |
| Center Forward, Right / Left Center Forward, Secondary Striker | FWD | CF | C / R / L / C |

A player's **primary position** for a season (needed for percentile populations) is the role with the most minutes. That is an analytics-layer rule, documented in FOOTBALL_ANALYTICS.md in Phase 4.

## 6. Minutes played

1. Period lengths: `Half End.timestamp` per period (elapsed time, including stoppage).
2. Convert a lineup clock value `MM:SS` in period *p* to elapsed seconds in that period by subtracting the period's clock offset (0, 45:00, 90:00, 105:00).
3. A spell with `to = null` ends at the end of the match's last period.
4. Spells are split per period (canonical `PositionSpell` lives within one period).
5. Minutes played = sum of spell durations. Shoot-out (period 5) is excluded.

### 6.1 Data-quality rules (found in Phase 2, decision D014)

The first ingestion of Premier League 2015/16 produced 91 validation failures out of 760 team-matches. Inspecting the raw lineups showed three StatsBomb data patterns:

| Pattern | Example | Rule |
|---|---|---|
| Spell continues after a red card | Simon Francis (Bournemouth) sent off at 56', but his spell runs to the final whistle via a later Tactical Shift | Playing time is cut at the player's **dismissal event** |
| Ghost spell after substitution | Coquelin substituted at half-time, then receives a new spell from a Tactical Shift recorded at 47:40 of the first half | Playing time is cut at the **substitution event** |
| Overlapping or backward spells | A spell from 45:12 (period 2) to 47:40 (period 1) | Overlaps are trimmed so no second is counted twice |
| Starters tagged "Tactical Shift" | Swansea starters with `start_reason = Tactical Shift` | A starter is anyone on the pitch at 00:00 of period 1 |

Each correction is logged as an ingestion warning (873 across the D011 slice: mostly "spell cut at exit" and "spell after exit removed").

### 6.2 Validation results (D011 slice, 1,517 matches)

| Check | Result |
|---|---|
| Score from goal + own-goal events = official score | **1,517 / 1,517** |
| 11 starters per team | **3,034 / 3,034** |
| Team minutes ≤ 11 × match length − on-pitch dismissals | **3,034 / 3,034** (0 excess) |
| Shortfall > 10 min (informational) | 9 team-matches, **all explained** by recorded "Player Off" events (treatment, injury after all substitutions were used, off-camera departures) |

Note: bench players and already-substituted players can be sent off. Such dismissals do not reduce the team on the pitch, and the validator accounts for that.

## 7. Paper validation against other providers

Each row checks that the canonical concept can be filled by other schemas. "–" means the provider does not record it, and the capability flag then reports it as unavailable.

| Canonical concept | StatsBomb | Wyscout v2 (public) | Opta (F24 event feed) |
|---|---|---|---|
| Pass + outcome | Pass, outcome absent = success | Pass (8) + tags 1801/1802 | type 1 + outcome 0/1 |
| Pass end location | `end_location` | 2nd `positions` entry | qualifiers 140/141 |
| Cross / through ball | flags | sub-event Cross / Smart pass | qualifiers 2 / 4 |
| Set piece | `pass.type` | Free kick group (3): corner, throw-in, goal kick, penalty | qualifiers 5, 6, 107, 124, 9 |
| Shot + goal | Shot / outcome | Shot (10) + tag 101 | types 13–16 |
| Provider xG | `statsbomb_xg` | – | contract-dependent qualifier |
| Take-on | Dribble | Duel: ground attacking + take-on tags | type 3 |
| Aerial duel won/lost | flag / Aerial Lost | Duel: air duel + won/lost tags | type 44 + outcome |
| Ground duel / tackle | Duel Tackle | Duel: ground defending | type 7 |
| Interception, clearance | yes | yes | types 8, 12 |
| Carry | yes | – | – |
| Pressure | yes | – | – (different concept) |
| Ball receipt | yes | – | – |
| Possession id | yes | – (derivable) | – (derivable) |
| Period lengths | Half End | last event time (approximate) | type 30 end events |
| Substitution timing | seconds | **minute only** | seconds |
| Match position per player | spells (25 slots) | **– (only player role GK/DF/MD/FW)** | formation positions |
| Birth date | – | yes | yes |
| Coordinates | 120 × 80, y down | 0–100, y down | 0–100, y up |

Conclusions for the canonical model, applied as v1.1 in [ARCHITECTURE.md](../ARCHITECTURE.md):

1. Add canonical types `ball_receipt`, `dribbled_past`, `miscontrol`, `dispossessed`, `own_goal`, and add a `duel_kind` (ground / aerial / loose_ball) instead of separate aerial events.
2. Split the old `play_context` into `set_piece` (action-level) and `possession_origin` (possession-level, optional).
3. Positions become `(line, role, side)`. Add the capability `position_granularity` (`slot` for StatsBomb/Opta, `line` for Wyscout v2).
4. Add capabilities `has_carries`, `has_ball_receipts`, and `minutes_precision` (`second` / `minute`).
5. Minutes-played precision varies by provider. Analytics must not compare minute-precision and second-precision data at sub-minute level.
