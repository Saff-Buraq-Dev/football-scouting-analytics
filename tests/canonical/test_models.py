from datetime import date

import pytest

from football_platform.canonical.enums import (
    EntityType,
    EventType,
    MatchStatus,
    Outcome,
    PositionLine,
)
from football_platform.canonical.identifiers import internal_id
from football_platform.canonical.models import (
    Appearance,
    Event,
    Match,
    Position,
    PositionSpell,
    Provenance,
)
from football_platform.canonical.pitch import Point

PROVENANCE = Provenance("test", "1", "release", "run")


def test_point_outside_pitch_is_rejected():
    with pytest.raises(ValueError):
        Point(106.0, 10.0)


def test_internal_ids_are_deterministic_and_scoped_by_entity_and_provider():
    assert internal_id("p", EntityType.PLAYER, 5) == internal_id("p", EntityType.PLAYER, "5")
    assert internal_id("p", EntityType.PLAYER, 5) != internal_id("p", EntityType.TEAM, 5)
    assert internal_id("p", EntityType.PLAYER, 5) != internal_id("q", EntityType.PLAYER, 5)


def test_match_rejects_identical_teams():
    with pytest.raises(ValueError):
        Match("m", "s", "c", date(2016, 1, 1), "t1", "t1", 0, 0, MatchStatus.PLAYED)


def test_minutes_played_sums_spells_and_excludes_shootout():
    gk = Position(PositionLine.GK)
    spells = (
        PositionSpell(gk, 1, 0, 2700),
        PositionSpell(gk, 2, 0, 2850),
        PositionSpell(gk, 5, 0, 600),
    )
    appearance = Appearance("m", "t", "p", True, spells)
    assert appearance.minutes_played == pytest.approx(92.5)


def test_spell_cannot_end_before_it_starts():
    with pytest.raises(ValueError):
        PositionSpell(Position(PositionLine.DEF), 1, 100, 50)


@pytest.mark.parametrize("event_type", [EventType.DUEL, EventType.SHOT, EventType.CARD])
def test_events_requiring_detail_are_validated(event_type):
    with pytest.raises(ValueError):
        Event("e", "m", 1, 0.0, "t", event_type, Outcome.UNKNOWN, PROVENANCE)


def test_invalid_period_is_rejected():
    with pytest.raises(ValueError):
        Event("e", "m", 6, 0.0, "t", EventType.PASS, Outcome.SUCCESS, PROVENANCE)
