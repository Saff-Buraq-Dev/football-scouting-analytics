# StatsBomb Open Data — Data Dictionary

Phase 1B deliverable. Profiled on **2026-10-04** at commit `4b73468f…`.

Profile sample: 12 matches, 43,696 events (two matches each from Premier League 2015/16, La Liga 2015/16, Serie A 2015/16, FA WSL 2023/24, FIFA World Cup 2022, UEFA Euro 2024, four of which have 360 data). Reproduce with:

```bash
cd scripts/discovery && python3 statsbomb_profile.py   # writes data/discovery/statsbomb_profile.json
```

The sample is for **schema discovery**. Percentages below describe the sample and are not football statistics. Official specification: `doc/` folder of the open-data repository.

Related: [STATSBOMB_COVERAGE.md](STATSBOMB_COVERAGE.md), [STATSBOMB_MAPPING.md](STATSBOMB_MAPPING.md).

---

## 1. Files

| File | Grain | Content |
|---|---|---|
| `data/competitions.json` | competition-season | ids, names, gender, international flag, availability timestamps, `match_available_360` |
| `data/matches/{competition_id}/{season_id}.json` | match | teams, score, date, kick-off, stage, stadium, referee, managers, `match_status_360` |
| `data/lineups/{match_id}.json` | team → player | squad incl. unused substitutes, cards, **position spells** |
| `data/events/{match_id}.json` | event | ~3,600 events per match |
| `data/three-sixty/{match_id}.json` | event | 360 freeze frame: visible area polygon + visible players |

## 2. Lineups

Per team: `team_id`, `team_name`, `lineup[]`. Per player:

| Field | Notes |
|---|---|
| `player_id`, `player_name` | full name, e.g. "Marco Asensio Willemsen" |
| `player_nickname` | commonly used name (may be null) |
| `jersey_number` | |
| `country` | `{id, name}` |
| `cards[]` | `time` (match clock), `card_type`, `reason`, `period` |
| `positions[]` | **position spells**: `position_id`, `position`, `from`, `to`, `from_period`, `to_period`, `start_reason`, `end_reason` |

Important semantics:

- **Unused substitutes have an empty `positions` list** (10 per team in the World Cup sample). Squad ≠ appearances.
- `from` / `to` are **match-clock strings "MM:SS"**, where period 2 restarts at 45:00, period 3 at 90:00 and period 4 at 105:00. First-half stoppage time therefore overlaps the second-half clock range.
- **`to` is null when the player finished the match** (`end_reason = "Final Whistle"`). The actual end time must come from the `Half End` event of the last period.
- `start_reason` values: Starting XI, Substitution - On (Tactical / Injury), Tactical Shift, Player On.
  `end_reason` values: Final Whistle, Substitution - Off (Tactical / Injury), Tactical Shift, Foul Committed (Red Card), Player Off, Player Off (Off Camera). A few spells show `end_reason = "Substitution - On (Tactical)"`, a data quirk to tolerate.
- **No birth date, height, preferred foot, or contract data.**

### Positions (25 in the specification, 23 seen in the sample)

Goalkeeper; Right/Left Back; Right/Left/Center Back (Right Center Back, Left Center Back, Center Back); Right/Left Wing Back; Right/Left/Center Defensive Midfield; Right/Left/Center Midfield (Right Center Midfield, Left Center Midfield, Right Midfield, Left Midfield); Right/Left/Center Attacking Midfield; Right/Left Wing; Center Forward, Right/Left Center Forward; Secondary Striker *(spec)*.

Positions are **formation slots**, not roles. "Right Midfield" in a 4-4-2 and "Right Wing" in a 4-3-3 can describe very similar players.

## 3. Events

### 3.1 Common fields

| Field | Fill | Notes |
|---|---|---|
| `id` | 100 % | UUID, unique globally |
| `index` | 100 % | order within the match |
| `period` | 100 % | 1, 2, 3, 4 (extra time), 5 (penalty shoot-out) |
| `timestamp` | 100 % | **time since period start** "HH:MM:SS.mmm" |
| `minute`, `second` | 100 % | match clock (period 2 starts at minute 45) |
| `type` | 100 % | event type `{id, name}` |
| `possession`, `possession_team` | 100 % | StatsBomb possession sequence number and owner |
| `play_pattern` | 100 % | how the **possession** started (see 3.4) |
| `team`, `player`, `position` | most | `player` absent on team-level events (Half Start/End, Starting XI…) |
| `location` | 100 % for on-ball types | `[x, y]` on 120 × 80 |
| `duration` | most | seconds |
| `under_pressure` | optional, **present only when true** | e.g. 15 % of passes, 31 % of carries |
| `counterpress` | optional, present only when true | pressure-type actions within 5 s of losing the ball |
| `off_camera`, `out` | optional, true only | event not visible on video / ball went out |
| `related_events` | most | UUIDs of linked events (e.g. pass ↔ ball receipt, duel ↔ dribble) |
| `tactics` | Starting XI / Tactical Shift | formation and lineup |

**Boolean flags are omitted when false.** A missing `under_pressure` means *not under pressure*, not unknown.

### 3.2 Coordinates

- Pitch 120 × 80 units, origin **top-left**, x towards the opponent goal, **y grows downwards**.
- **Every team's events are oriented attacking left→right**, so no per-half flipping is needed.
- End locations: `pass.end_location`, `carry.end_location`, `shot.end_location` (3-D `[x, y, z]` at the goal mouth), `goalkeeper.end_location`.

### 3.3 Event types (sample frequency)

| Type | Share | Detail object | Notes |
|---|---:|---|---|
| Pass | 28.2 % | `pass` | see 3.5 |
| Ball Receipt* | 26.7 % | `ball_receipt` | reception of a pass. `outcome` only when Incomplete |
| Carry | 22.3 % | `carry.end_location` | player moving with the ball. StatsBomb-specific |
| Pressure | 8.7 % | – | pressing an opponent in possession. StatsBomb-specific |
| Ball Recovery | 2.7 % | `ball_recovery` | `recovery_failure` flag |
| Duel | 1.8 % | `duel.type`, `duel.outcome` | **only "Tackle" and "Aerial Lost"** (see 3.6) |
| Clearance | 1.3 % | `clearance` | body part, `aerial_won` |
| Block | 1.1 % | `block` | `deflection`, `offensive`, `save_block` |
| Dribble | 0.9 % | `dribble.outcome` | **take-on attempt** (Complete/Incomplete), `nutmeg`, `overrun` |
| Goal Keeper | 0.9 % | `goalkeeper` | type (Shot Faced, Shot Saved, Goal Conceded, Collected, Punch, Keeper Sweeper…), outcome, position, technique |
| Shot | 0.7 % | `shot` | see 3.7 |
| Miscontrol | 0.7 % | – | bad touch losing the ball |
| Foul Committed / Foul Won | 0.6 % each | | card, penalty, advantage, offensive/defensive |
| Dispossessed | 0.6 % | – | ball lost to a tackle |
| Interception | 0.6 % | `interception.outcome` | |
| Dribbled Past | 0.5 % | – | defender beaten by a take-on |
| Substitution | 0.2 % | `replacement`, `outcome` (Tactical/Injury) | |
| 50/50 | 0.1 % | `50_50.outcome` | contested loose ball |
| Half Start / Half End | 0.1 % | – | one per team per period. **Half End timestamp = actual period length** |
| Starting XI, Tactical Shift | | `tactics` | formation, lineup |
| Injury Stoppage, Referee Ball-Drop, Player Off/On, Bad Behaviour, Shield, Error, Offside | < 0.1 % | | |
| Own Goal For / Own Goal Against | rare | – | **own goals are not Shot events** |

### 3.4 Play pattern (possession origin)

Regular Play, From Throw In, From Free Kick, From Goal Kick, From Kick Off, From Corner, From Keeper, From Counter, Other.

It describes how the **possession** began. It is not a property of the single action. A shot ten passes after a corner still has `From Corner`.

### 3.5 Pass

| Attribute | Fill | Semantics |
|---|---|---|
| `recipient` | 95 % | intended/actual receiver |
| `length`, `angle`, `end_location`, `height` | 100 % | height: Ground / Low / High |
| `body_part` | 94 % | Right/Left Foot, Head, Keeper Arm, Drop Kick, Other, No Touch |
| **`outcome`** | **19 %** | **absent = completed.** Values: Incomplete, Out, Pass Offside, Unknown, Injury Clearance |
| `type` | 18 % | set-piece or special origin: Throw-in, Free Kick, Corner, Goal Kick, Kick Off, Recovery, Interception. **Absent = open-play pass** |
| `technique` | 1 % | Through Ball, Inswinging, Outswinging, Straight |
| flags (true only) | | `cross`, `switch`, `cut_back`, `through_ball`, `shot_assist`, `goal_assist`, `aerial_won`, `deflected`, `miscommunication`, `no_touch` |
| `assisted_shot_id` | 2 % | links the pass to the shot it set up |

### 3.6 Duels and aerials

- `Duel` events carry `type` = **Tackle** or **Aerial Lost** only.
- **Aerial duels won are not Duel events.** They appear as an `aerial_won` flag on the winner's Pass, Clearance, Shot or Miscontrol.
- `duel.outcome` is present only for tackles (Won, Lost In Play, Lost Out, Success In Play, Success Out). An Aerial Lost has no outcome.
- Take-ons are `Dribble` (attacker) and `Dribbled Past` (defender beaten), not duels.

Consequence: "aerial duels won %" needs Aerial Lost events **plus** `aerial_won` flags across four event types.

### 3.7 Shot

| Attribute | Fill | Semantics |
|---|---|---|
| `statsbomb_xg` | 100 % | provider xG |
| `outcome` | 100 % | Goal, Saved, Blocked, Off T, Wayward, Post, Saved to Post, Saved Off Target |
| `type` | 100 % | Open Play, Free Kick, Penalty (also Corner, Kick Off in spec) |
| `body_part`, `technique` | 100 % | |
| `end_location` | 100 % | 3-D |
| `key_pass_id` | 73 % | the pass that set up the shot (absent for unassisted shots) |
| **`freeze_frame`** | 99 % | player positions **at the moment of the shot** (location, player, position, teammate). **Present in all seasons, including 2015/16, independent of 360** |
| flags | | `first_time`, `one_on_one`, `open_goal`, `aerial_won`, `deflected` |

### 3.8 Cards

Cards are recorded on `Foul Committed.card` and `Bad Behaviour.card` (Yellow Card, Second Yellow, Red Card) **and** in lineups `cards[]`. A sending-off ends the player's last position spell with `end_reason = "Foul Committed (Red Card)"` (or the equivalent for other dismissals).

## 4. 360 freeze frames

Per event (`event_uuid`): `visible_area` (polygon of the broadcast camera view) and `freeze_frame[]` with `teammate`, `actor`, `keeper`, `location`.

- **Players are anonymous.** There is no player id, only team side and role flags.
- Only players **visible on the broadcast** are included (~15 per frame in the sample).
- Available for 12 competition-seasons (see the coverage audit), none of them a complete league season.

## 5. Known limitations for this project

| Limitation | Impact |
|---|---|
| No birth date / height / foot | No age filters or age curves |
| Positions are formation slots | Role must be inferred carefully. See mapping |
| xG is StatsBomb's model | Valid only within StatsBomb data (D007) |
| Pressure, Carry, Ball Receipt are StatsBomb-specific | Metrics using them are capability-gated |
| Aerial wins are flags, not events | Mapping must combine them explicitly |
| `minute`/lineup clock ≠ elapsed time | Minutes played needs period lengths from Half End events |
| Event collection is human-coded from video | Subjective edge cases (e.g. what counts as pressure) |
