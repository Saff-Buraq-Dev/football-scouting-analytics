"""Minutes played is the denominator of every per-90 metric, so its edge cases are tested here."""

import pytest

from football_platform.providers.statsbomb.lineups import (
    clock_to_period_elapsed,
    map_lineups,
    split_spell,
)
from tests.providers.statsbomb.factories import lineup_player, spell

# First half 47 min (2 min stoppage), second half 49 min (4 min stoppage).
PERIODS = {1: 47 * 60.0, 2: 49 * 60.0}
MATCH_MINUTES = 47 + 49


def appearance_for(positions, periods=PERIODS):
    raw = [{"team_id": 100, "team_name": "Home FC", "lineup": [lineup_player(1, positions)]}]
    result = map_lineups(raw, "match-1", periods)
    return result.appearances[0], result


@pytest.mark.parametrize(
    ("clock", "period", "expected"),
    [("00:00", 1, 0), ("46:30", 1, 2790), ("45:00", 2, 0), ("68:54", 2, 1434), ("95:00", 3, 300)],
)
def test_clock_to_period_elapsed(clock, period, expected):
    assert clock_to_period_elapsed(clock, period) == expected


def test_full_match_player_gets_actual_match_length_including_stoppage_time():
    appearance, _ = appearance_for([spell("Center Back", "00:00", 1, None, None)])
    assert appearance.is_starter
    assert appearance.minutes_played == pytest.approx(MATCH_MINUTES)
    assert [s.period for s in appearance.position_spells] == [1, 2]


def test_second_half_substitute():
    positions = [spell("Left Wing", "68:54", 2, None, None, start_reason="Substitution - On (Tactical)")]
    appearance, _ = appearance_for(positions)
    assert not appearance.is_starter
    # On at 23:54 of a 49:00 second half -> 25:06 played.
    assert appearance.minutes_played == pytest.approx(25.1)


def test_substituted_in_first_half_stoppage_time():
    # Clock 46:30 in period 1 = 46.5 elapsed minutes: the overlap with the second-half clock must not matter.
    positions = [spell("Right Back", "00:00", 1, "46:30", 1, end_reason="Substitution - Off (Injury)")]
    appearance, _ = appearance_for(positions)
    assert appearance.minutes_played == pytest.approx(46.5)


def test_red_card_ends_playing_time():
    positions = [spell("Center Forward", "00:00", 1, "60:00", 2, end_reason="Foul Committed (Red Card)")]
    appearance, _ = appearance_for(positions)
    assert appearance.minutes_played == pytest.approx(47 + 15)


def test_tactical_shift_keeps_total_minutes_and_records_both_positions():
    positions = [
        spell("Right Wing Back", "00:00", 1, "68:54", 2, end_reason="Tactical Shift"),
        spell("Left Wing", "68:54", 2, None, None, start_reason="Tactical Shift"),
    ]
    appearance, _ = appearance_for(positions)
    assert appearance.minutes_played == pytest.approx(MATCH_MINUTES)
    assert {s.position.role.value for s in appearance.position_spells} == {"WB", "W"}


def test_unused_substitute_has_no_minutes():
    appearance, _ = appearance_for([])
    assert not appearance.played
    assert appearance.minutes_played == 0


def test_extra_time_counts_and_shootout_does_not():
    periods = {1: 2700.0, 2: 2700.0, 3: 900.0, 4: 900.0, 5: 600.0}
    appearance, _ = appearance_for([spell("Goalkeeper", "00:00", 1, None, None)], periods)
    assert appearance.minutes_played == pytest.approx(120)


def test_spell_end_beyond_period_is_clamped_with_warning():
    warnings = []
    spells = split_spell(spell("Goalkeeper", "00:00", 1, "50:00", 1), {1: 47 * 60.0, 2: 2700.0}, warnings, "p")
    assert spells[0].end_s == 47 * 60
    assert warnings


class TestDataQualityRules:
    """Patterns found in real Premier League 2015/16 lineups (docs/data/STATSBOMB_MAPPING.md §6)."""

    def test_spell_continuing_after_red_card_is_cut_at_the_dismissal_event(self):
        # Lineup says the player stays on via a Tactical Shift; the red card event says otherwise.
        positions = [
            spell("Right Back", "00:00", 1, "66:54", 2, end_reason="Tactical Shift"),
            spell("Center Back", "66:54", 2, None, None, start_reason="Tactical Shift"),
        ]
        raw = [{"team_id": 100, "team_name": "Home FC", "lineup": [lineup_player(1, positions)]}]
        exits = {1: (2, 11 * 60.0)}  # sent off at 56:00 on the match clock
        appearance = map_lineups(raw, "m", PERIODS, exits).appearances[0]
        assert appearance.minutes_played == pytest.approx(47 + 11)

    def test_ghost_spell_after_substitution_is_removed(self):
        positions = [
            spell("Center Defensive Midfield", "00:00", 1, "45:00", 2, end_reason="Substitution - Off (Tactical)"),
            spell("Center Defensive Midfield", "47:40", 1, None, None, start_reason="Tactical Shift"),
        ]
        raw = [{"team_id": 100, "team_name": "Home FC", "lineup": [lineup_player(1, positions)]}]
        appearance = map_lineups(raw, "m", PERIODS, {1: (2, 0.0)}).appearances[0]
        assert appearance.minutes_played == pytest.approx(47)

    def test_overlapping_spells_are_not_double_counted(self):
        positions = [
            spell("Center Attacking Midfield", "00:00", 1, "45:12", 2, end_reason="Tactical Shift"),
            spell("Left Wing", "45:12", 2, "47:40", 1, start_reason="Tactical Shift"),  # runs backwards
            spell("Center Attacking Midfield", "47:40", 1, None, None, start_reason="Tactical Shift"),
        ]
        appearance, result = appearance_for(positions)
        assert appearance.minutes_played == pytest.approx(MATCH_MINUTES)
        assert any("overlapping" in w for w in result.warnings)

    def test_starter_tagged_as_tactical_shift_is_still_a_starter(self):
        appearance, _ = appearance_for([spell("Goalkeeper", "00:00", 1, None, None, start_reason="Tactical Shift")])
        assert appearance.is_starter


def test_exit_times_take_substitutions_and_dismissals_from_events():
    from football_platform.providers.statsbomb.lineups import exit_times_from_events
    from tests.providers.statsbomb.factories import raw_event

    events = [
        raw_event("Substitution", player_id=1, period=2, timestamp="00:20:00.000",
                  substitution={"replacement": {"id": 9}, "outcome": {"name": "Tactical"}}),
        raw_event("Foul Committed", player_id=2, period=1, timestamp="00:30:00.500",
                  foul_committed={"card": {"name": "Red Card"}}),
        raw_event("Foul Committed", player_id=3, foul_committed={"card": {"name": "Yellow Card"}}),
    ]
    assert exit_times_from_events(events) == {1: (2, 1200.0), 2: (1, 1800.5)}
