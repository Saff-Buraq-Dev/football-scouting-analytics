from datetime import date

from football_platform.canonical.enums import (
    CardType, EventType, MatchStatus, Outcome, PositionLine, ShotOutcome,
)
from football_platform.canonical.models import (
    Appearance, Event, Match, Position, PositionSpell, Provenance, ShotDetail,
)
from football_platform.pipeline.validation import check_minutes, check_score, check_starters
from football_platform.providers.base import MatchBundle

P = Provenance("t", "1", "r", "run")
HALF = 45 * 60.0


def match(home_score=1, away_score=1):
    return Match("m", "s", "c", date(2016, 1, 1), "home", "away", home_score, away_score, MatchStatus.PLAYED)


def event(event_type, team="home", period=1, time_s=60.0, **kw):
    return Event(f"e{id(kw)}{event_type}{time_s}{team}", "m", period, time_s, team, event_type, Outcome.UNKNOWN, P, **kw)


def goal(team, period=1):
    return event(EventType.SHOT, team, period, shot_detail=ShotDetail(ShotOutcome.GOAL))


def period_ends():
    return [event(EventType.PERIOD_END, t, p, HALF) for p in (1, 2) for t in ("home", "away")]


def players(team, count=11, minutes_each=90.0, starters=11):
    spell_s = minutes_each * 60 / 2
    return [
        Appearance("m", team, f"{team}{i}", i < starters,
                   (PositionSpell(Position(PositionLine.MID), 1, 0, spell_s),
                    PositionSpell(Position(PositionLine.MID), 2, 0, spell_s)))
        for i in range(count)
    ]


def bundle(events, appearances, m=None):
    return MatchBundle(m or match(), (), tuple(appearances), tuple(events), ())


def test_score_counts_own_goals_for_the_opponent_and_ignores_shootouts():
    events = [goal("home"), event(EventType.OWN_GOAL, "home"), goal("away", period=5)]
    assert check_score(bundle(events, [])) == []


def test_score_mismatch_is_reported():
    assert check_score(bundle([goal("home")], [], match(2, 0)))[0].check == "score"


def test_full_teams_pass_minutes_check():
    apps = players("home") + players("away")
    assert check_minutes(bundle(period_ends(), apps)) == []


def test_twelve_players_counted_is_an_excess():
    apps = players("home", count=12) + players("away")
    (issue,) = check_minutes(bundle(period_ends(), apps))
    assert issue.check == "minutes_excess"


def test_dismissal_reduces_expected_minutes():
    red = event(EventType.CARD, "home", 2, HALF / 3, card_type=CardType.RED, player_id="home0")
    apps = players("home", count=10) + [
        Appearance("m", "home", "home10", True,
                   (PositionSpell(Position(PositionLine.DEF), 1, 0, HALF),
                    PositionSpell(Position(PositionLine.DEF), 2, 0, HALF / 3)))
    ] + players("away")
    assert check_minutes(bundle(period_ends() + [red], apps)) == []


def test_starters_check():
    apps = players("home", starters=10) + players("away")
    (issue,) = check_starters(bundle([], apps))
    assert issue.check == "starters"


def test_dismissal_of_a_bench_player_does_not_reduce_expected_minutes():
    red = event(EventType.CARD, "home", 2, 600.0, card_type=CardType.RED, player_id="bench-player")
    apps = players("home") + players("away")
    assert check_minutes(bundle(period_ends() + [red], apps)) == []
