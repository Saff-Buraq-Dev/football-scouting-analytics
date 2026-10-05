"""Football consistency checks on canonical match bundles.

These checks catch mapping errors that unit tests on synthetic data cannot:
- the score implied by goal events equals the official score;
- each team's minutes never exceed 11 players x actual match length, minus
  time lost to dismissals ("minutes_excess" = more than 11 players counted);
- large shortfalls are reported separately ("minutes_shortfall"). They are
  often real football (treatment off the pitch, injury after all substitutions
  were used) but can also reveal missing lineup data;
- each team names exactly 11 starters.
Failures are reported, not raised: one odd match must not block a season.
"""

from __future__ import annotations

from dataclasses import dataclass

from football_platform.canonical.enums import CardType, EventType, ShotOutcome
from football_platform.canonical.models import SHOOTOUT_PERIOD, Event
from football_platform.providers.base import MatchBundle

PLAYERS_PER_TEAM = 11
# Lineup clock values have 1 s precision per spell boundary.
MINUTES_TOLERANCE = 1.0
# Shortfalls up to this are expected (treatment breaks, permanent injuries).
SHORTFALL_REPORT_THRESHOLD = 10.0
DISMISSALS = {CardType.RED, CardType.SECOND_YELLOW}


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    match_id: str
    check: str
    detail: str


def _period_lengths(events: tuple[Event, ...]) -> dict[int, float]:
    lengths: dict[int, float] = {}
    for event in events:
        if event.type is EventType.PERIOD_END and event.period != SHOOTOUT_PERIOD:
            lengths[event.period] = max(event.time_s, lengths.get(event.period, 0.0))
    return lengths


def check_score(bundle: MatchBundle) -> list[ValidationIssue]:
    match = bundle.match
    goals = {match.home_team_id: 0, match.away_team_id: 0}
    opponent = {match.home_team_id: match.away_team_id, match.away_team_id: match.home_team_id}
    for event in bundle.events:
        if event.period == SHOOTOUT_PERIOD:
            continue
        if event.type is EventType.SHOT and event.shot_detail.outcome is ShotOutcome.GOAL:
            goals[event.team_id] += 1
        elif event.type is EventType.OWN_GOAL:
            goals[opponent[event.team_id]] += 1
    expected = (match.home_score, match.away_score)
    actual = (goals[match.home_team_id], goals[match.away_team_id])
    if actual != expected:
        return [ValidationIssue(match.id, "score", f"events give {actual}, official score {expected}")]
    return []


def check_minutes(bundle: MatchBundle) -> list[ValidationIssue]:
    match = bundle.match
    lengths = _period_lengths(bundle.events)
    if not lengths:
        return [ValidationIssue(match.id, "minutes_excess", "no period end events")]
    match_seconds = sum(lengths.values())

    def remaining_after(event: Event) -> float:
        later = sum(length for period, length in lengths.items() if period > event.period)
        return max(lengths.get(event.period, 0.0) - event.time_s, 0.0) + later

    # A dismissal only reduces the team if the player was on the pitch at that
    # moment (players on the bench or already substituted can also be sent off).
    spells_by_player = {a.player_id: a.position_spells for a in bundle.appearances}

    def on_pitch(event: Event) -> bool:
        return any(
            s.period == event.period and s.start_s <= event.time_s <= s.end_s + MINUTES_TOLERANCE * 60
            for s in spells_by_player.get(event.player_id, ())
        )

    issues = []
    for team_id in (match.home_team_id, match.away_team_id):
        lost = sum(
            remaining_after(e)
            for e in bundle.events
            if e.type is EventType.CARD and e.card_type in DISMISSALS and e.team_id == team_id
            and e.player_id is not None and e.period != SHOOTOUT_PERIOD and on_pitch(e)
        )
        expected = (PLAYERS_PER_TEAM * match_seconds - lost) / 60.0
        actual = sum(a.minutes_played for a in bundle.appearances if a.team_id == team_id)
        detail = f"team {team_id}: {actual:.1f} min, expected {expected:.1f}"
        if actual - expected > MINUTES_TOLERANCE:
            issues.append(ValidationIssue(match.id, "minutes_excess", detail))
        elif expected - actual > SHORTFALL_REPORT_THRESHOLD:
            issues.append(ValidationIssue(match.id, "minutes_shortfall", detail))
    return issues


def check_starters(bundle: MatchBundle) -> list[ValidationIssue]:
    issues = []
    for team_id in (bundle.match.home_team_id, bundle.match.away_team_id):
        starters = sum(1 for a in bundle.appearances if a.team_id == team_id and a.is_starter)
        if starters != PLAYERS_PER_TEAM:
            issues.append(ValidationIssue(bundle.match.id, "starters", f"team {team_id}: {starters} starters"))
    return issues


def validate_bundle(bundle: MatchBundle) -> list[ValidationIssue]:
    return check_score(bundle) + check_minutes(bundle) + check_starters(bundle)
