import pytest

from football_platform.canonical.enums import (
    BodyPart,
    CardType,
    DuelKind,
    EntityType,
    EventType,
    GoalkeeperActionKind,
    Outcome,
    PossessionOrigin,
    SetPiece,
    ShotOutcome,
)
from football_platform.canonical.identifiers import internal_id
from football_platform.canonical.pitch import Point
from football_platform.providers.statsbomb.events import map_events, parse_timestamp
from tests.providers.statsbomb.factories import half_end, raw_event


def map_one(raw):
    result = map_events([raw], "match-1", "commit-x", "run-1")
    assert len(result.events) == 1
    return result.events[0], result


def test_parse_timestamp():
    assert parse_timestamp("00:48:00.822") == pytest.approx(2880.822)


class TestPass:
    def test_pass_without_outcome_is_completed(self):
        event, _ = map_one(raw_event("Pass", location=[60, 40], **{"pass": {"end_location": [80, 40]}}))
        assert event.type is EventType.PASS
        assert event.outcome is Outcome.SUCCESS
        assert event.start == Point(52.5, 34.0)
        assert event.end == Point(70.0, 34.0)

    @pytest.mark.parametrize("name", ["Incomplete", "Out", "Pass Offside"])
    def test_failed_pass_outcomes(self, name):
        raw = raw_event("Pass", **{"pass": {"end_location": [80, 40], "outcome": {"name": name}}})
        assert map_one(raw)[0].outcome is Outcome.FAIL

    def test_injury_clearance_is_not_a_pass_attempt(self):
        raw = raw_event("Pass", **{"pass": {"end_location": [80, 40], "outcome": {"name": "Injury Clearance"}}})
        assert map_one(raw)[0].outcome is Outcome.NOT_APPLICABLE

    def test_corner_is_a_set_piece_but_recovery_pass_is_open_play(self):
        corner = raw_event("Pass", **{"pass": {"end_location": [110, 40], "type": {"name": "Corner"}}})
        recovery = raw_event("Pass", **{"pass": {"end_location": [70, 40], "type": {"name": "Recovery"}}})
        assert map_one(corner)[0].set_piece is SetPiece.CORNER
        assert map_one(recovery)[0].set_piece is None

    def test_pass_detail_flags_and_links(self):
        raw = raw_event(
            "Pass",
            **{
                "pass": {
                    "end_location": [110, 30],
                    "cross": True,
                    "technique": {"name": "Through Ball"},
                    "shot_assist": True,
                    "assisted_shot_id": "shot-uuid",
                    "recipient": {"id": 7, "name": "Seven"},
                    "height": {"name": "High Pass"},
                    "body_part": {"name": "Left Foot"},
                }
            },
        )
        event, _ = map_one(raw)
        detail = event.pass_detail
        assert detail.is_cross and detail.is_through_ball and detail.is_shot_assist
        assert not detail.is_goal_assist
        assert detail.recipient_id == internal_id("statsbomb_open", EntityType.PLAYER, 7)
        assert detail.assisted_shot_event_id == internal_id("statsbomb_open", EntityType.EVENT, "shot-uuid")
        assert event.body_part is BodyPart.FOOT_LEFT


class TestShot:
    def test_goal_from_penalty_carries_provider_xg(self):
        raw = raw_event(
            "Shot",
            location=[108, 40],
            **{
                "shot": {
                    "outcome": {"name": "Goal"},
                    "type": {"name": "Penalty"},
                    "statsbomb_xg": 0.78,
                    "end_location": [120, 38, 0.5],
                    "body_part": {"name": "Right Foot"},
                }
            },
        )
        event, _ = map_one(raw)
        assert event.outcome is Outcome.SUCCESS
        assert event.shot_detail.outcome is ShotOutcome.GOAL
        assert event.shot_detail.end_z == 0.5
        assert event.set_piece is SetPiece.PENALTY
        (metric,) = event.provider_metrics
        assert (metric.metric_key, metric.value, metric.source_provider) == ("xg", 0.78, "statsbomb_open")

    def test_open_play_shot_saved(self):
        raw = raw_event("Shot", **{"shot": {"outcome": {"name": "Saved"}, "type": {"name": "Open Play"}}})
        event, _ = map_one(raw)
        assert event.outcome is Outcome.FAIL
        assert event.set_piece is None

    def test_unknown_shot_outcome_fails_loudly(self):
        with pytest.raises(ValueError):
            map_one(raw_event("Shot", **{"shot": {"outcome": {"name": "Teleported"}}}))


class TestDuelsAndAerials:
    def test_aerial_lost_is_an_aerial_duel_failure(self):
        event, _ = map_one(raw_event("Duel", duel={"type": {"name": "Aerial Lost"}}))
        assert (event.type, event.duel_kind, event.outcome) == (EventType.DUEL, DuelKind.AERIAL, Outcome.FAIL)

    def test_aerial_won_is_a_flag_not_an_extra_event(self):
        result = map_events(
            [raw_event("Clearance", clearance={"aerial_won": True, "body_part": {"name": "Head"}})],
            "m", "c", "r",
        )
        assert len(result.events) == 1
        assert result.events[0].aerial_won is True

    @pytest.mark.parametrize(("name", "expected"), [("Won", Outcome.SUCCESS), ("Lost In Play", Outcome.FAIL)])
    def test_tackle_outcome(self, name, expected):
        event, _ = map_one(raw_event("Duel", duel={"type": {"name": "Tackle"}, "outcome": {"name": name}}))
        assert event.duel_kind is DuelKind.GROUND
        assert event.outcome is expected

    def test_fifty_fifty_is_a_loose_ball_duel(self):
        event, _ = map_one(raw_event("50/50", **{"50_50": {"outcome": {"name": "Success To Team"}}}))
        assert (event.duel_kind, event.outcome) == (DuelKind.LOOSE_BALL, Outcome.SUCCESS)


class TestOtherTypes:
    def test_own_goal_against_is_own_goal_and_own_goal_for_is_kept_as_other(self):
        result = map_events([raw_event("Own Goal Against"), raw_event("Own Goal For")], "m", "c", "r")
        assert [e.type for e in result.events] == [EventType.OWN_GOAL, EventType.OTHER]
        assert result.events[1].provider_event_type == "Own Goal For"

    def test_foul_with_card_emits_foul_and_card(self):
        raw = raw_event("Foul Committed", foul_committed={"card": {"name": "Second Yellow"}})
        result = map_events([raw], "m", "c", "r")
        foul, card = result.events
        assert foul.type is EventType.FOUL_COMMITTED
        assert (card.type, card.card_type) == (EventType.CARD, CardType.SECOND_YELLOW)
        assert card.id != foul.id

    def test_bad_behaviour_card(self):
        event, _ = map_one(raw_event("Bad Behaviour", bad_behaviour={"card": {"name": "Red Card"}}))
        assert event.card_type is CardType.RED

    def test_goalkeeper_save(self):
        raw = raw_event("Goal Keeper", goalkeeper={"type": {"name": "Shot Saved"}, "outcome": {"name": "Success"}})
        event, _ = map_one(raw)
        assert event.goalkeeper_action_kind is GoalkeeperActionKind.SAVE
        assert event.outcome is Outcome.SUCCESS

    def test_unknown_type_is_kept_as_other(self):
        event, _ = map_one(raw_event("Brand New Type"))
        assert event.type is EventType.OTHER
        assert event.provider_event_type == "Brand New Type"

    def test_absent_flags_mean_false_and_present_flags_are_kept(self):
        event, _ = map_one(raw_event("Pressure", counterpress=True))
        assert event.under_pressure is False
        assert event.provider_qualifiers == {"counterpress": True}


def test_period_lengths_come_from_half_end_events():
    events = half_end(1, "00:47:10.500") + half_end(2, "00:49:24.782")
    result = map_events(events, "m", "c", "r")
    assert result.period_lengths_s == pytest.approx({1: 2830.5, 2: 2964.782})


def test_unknown_play_pattern_is_warned_not_dropped():
    event, result = map_one(raw_event("Pressure", play_pattern="From Space"))
    assert event.possession_origin is None
    assert any("From Space" in w for w in result.warnings)


def test_mapping_is_deterministic():
    raw = raw_event("Pressure")
    first = map_events([raw], "m", "c", "r").events[0]
    second = map_events([raw], "m", "c", "r").events[0]
    assert first == second
    assert first.possession_origin is PossessionOrigin.REGULAR_PLAY
