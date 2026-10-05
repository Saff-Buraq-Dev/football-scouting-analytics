"""StatsBomb events -> canonical events (docs/data/STATSBOMB_MAPPING.md §3-4).

Conventions:
- StatsBomb omits boolean flags when false, so an absent flag maps to False.
- Unknown provider values map to None/UNKNOWN and a warning is recorded, so
  nothing is silently discarded. Exception: an unknown shot outcome raises,
  because goals (and therefore scores) depend on it.
- No event is dropped. Types without a canonical equivalent become OTHER.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from football_platform.canonical.enums import (
    BodyPart,
    CardType,
    DuelKind,
    EntityType,
    EventType,
    GoalkeeperActionKind,
    Outcome,
    PassHeight,
    PossessionOrigin,
    SetPiece,
    ShotOutcome,
)
from football_platform.canonical.identifiers import internal_id
from football_platform.canonical.models import (
    Event,
    PassDetail,
    Provenance,
    ProviderMetric,
    ShotDetail,
)
from football_platform.providers.statsbomb.constants import PROVIDER, XG_MODEL_VERSION
from football_platform.providers.statsbomb.coordinates import to_canonical_point

RawEvent = dict[str, Any]

POSSESSION_ORIGIN = {
    "Regular Play": PossessionOrigin.REGULAR_PLAY,
    "From Throw In": PossessionOrigin.THROW_IN,
    "From Free Kick": PossessionOrigin.FREE_KICK,
    "From Goal Kick": PossessionOrigin.GOAL_KICK,
    "From Kick Off": PossessionOrigin.KICK_OFF,
    "From Corner": PossessionOrigin.CORNER,
    "From Keeper": PossessionOrigin.KEEPER,
    "From Counter": PossessionOrigin.COUNTER,
    "Other": PossessionOrigin.OTHER,
}

SET_PIECE = {
    "Throw-in": SetPiece.THROW_IN,
    "Free Kick": SetPiece.FREE_KICK,
    "Corner": SetPiece.CORNER,
    "Goal Kick": SetPiece.GOAL_KICK,
    "Kick Off": SetPiece.KICK_OFF,
    "Penalty": SetPiece.PENALTY,
}
# pass.type / shot.type values that describe the action but are open play.
OPEN_PLAY_TYPES = {"Recovery", "Interception", "Open Play"}

BODY_PART = {
    "Right Foot": BodyPart.FOOT_RIGHT,
    "Left Foot": BodyPart.FOOT_LEFT,
    "Head": BodyPart.HEAD,
    "Keeper Arm": BodyPart.HANDS,
    "Both Hands": BodyPart.HANDS,
    "Left Hand": BodyPart.HANDS,
    "Right Hand": BodyPart.HANDS,
    "Drop Kick": BodyPart.OTHER,  # kicked from the hands; foot side not recorded
    "Chest": BodyPart.OTHER,
    "No Touch": BodyPart.OTHER,
    "Other": BodyPart.OTHER,
}

PASS_HEIGHT = {
    "Ground Pass": PassHeight.GROUND,
    "Low Pass": PassHeight.LOW,
    "High Pass": PassHeight.HIGH,
}

PASS_OUTCOME = {
    None: Outcome.SUCCESS,  # StatsBomb omits the outcome for completed passes
    "Incomplete": Outcome.FAIL,
    "Out": Outcome.FAIL,
    "Pass Offside": Outcome.FAIL,
    "Unknown": Outcome.UNKNOWN,
    "Injury Clearance": Outcome.NOT_APPLICABLE,  # deliberately kicked out; not a pass attempt
}

# Shared by Duel (tackle) and Interception outcomes.
CONTEST_OUTCOME = {
    "Won": Outcome.SUCCESS,
    "Success": Outcome.SUCCESS,
    "Success In Play": Outcome.SUCCESS,
    "Success Out": Outcome.SUCCESS,
    "Lost": Outcome.FAIL,
    "Lost In Play": Outcome.FAIL,
    "Lost Out": Outcome.FAIL,
}

FIFTY_FIFTY_OUTCOME = {
    "Won": Outcome.SUCCESS,
    "Success To Team": Outcome.SUCCESS,
    "Lost": Outcome.FAIL,
    "Success To Opposition": Outcome.FAIL,
}

SHOT_OUTCOME = {
    "Goal": ShotOutcome.GOAL,
    "Saved": ShotOutcome.SAVED,
    "Saved to Post": ShotOutcome.SAVED,
    "Saved Off Target": ShotOutcome.SAVED,
    "Blocked": ShotOutcome.BLOCKED,
    "Off T": ShotOutcome.OFF_TARGET,
    "Post": ShotOutcome.POST,
    "Wayward": ShotOutcome.WAYWARD,
}

GOALKEEPER_KIND = {
    "Shot Faced": GoalkeeperActionKind.SHOT_FACED,
    "Shot Saved": GoalkeeperActionKind.SAVE,
    "Save": GoalkeeperActionKind.SAVE,
    "Shot Saved to Post": GoalkeeperActionKind.SAVE,
    "Saved to Post": GoalkeeperActionKind.SAVE,
    "Shot Saved Off Target": GoalkeeperActionKind.SAVE,
    "Penalty Saved": GoalkeeperActionKind.SAVE,
    "Penalty Saved to Post": GoalkeeperActionKind.SAVE,
    "Goal Conceded": GoalkeeperActionKind.GOAL_CONCEDED,
    "Penalty Conceded": GoalkeeperActionKind.GOAL_CONCEDED,
    "Collected": GoalkeeperActionKind.CLAIM,
    "Punch": GoalkeeperActionKind.PUNCH,
    "Keeper Sweeper": GoalkeeperActionKind.SWEEPER,
    "Smother": GoalkeeperActionKind.SMOTHER,
}

GOALKEEPER_OUTCOME = {
    "Success": Outcome.SUCCESS,
    "Success In Play": Outcome.SUCCESS,
    "Success Out": Outcome.SUCCESS,
    "Claim": Outcome.SUCCESS,
    "Clear": Outcome.SUCCESS,
    "Collected Twice": Outcome.SUCCESS,
    "In Play Safe": Outcome.SUCCESS,
    "Saved Twice": Outcome.SUCCESS,
    "Punched out": Outcome.SUCCESS,
    "Won": Outcome.SUCCESS,
    "Fail": Outcome.FAIL,
    "In Play Danger": Outcome.FAIL,
    "Touched In": Outcome.FAIL,
    "Lost In Play": Outcome.FAIL,
    "Lost Out": Outcome.FAIL,
    # "No Touch", "Touched Out" have no clear success meaning -> UNKNOWN
}

CARD_TYPE = {
    "Yellow Card": CardType.YELLOW,
    "Second Yellow": CardType.SECOND_YELLOW,
    "Red Card": CardType.RED,
}

# Event types mapped 1:1 with a fixed outcome and no detail.
SIMPLE_TYPES: dict[str, tuple[EventType, Outcome]] = {
    "Dribbled Past": (EventType.DRIBBLED_PAST, Outcome.FAIL),
    "Dispossessed": (EventType.DISPOSSESSED, Outcome.FAIL),
    "Own Goal Against": (EventType.OWN_GOAL, Outcome.NOT_APPLICABLE),
    "Foul Won": (EventType.FOUL_WON, Outcome.NOT_APPLICABLE),
    "Half Start": (EventType.PERIOD_START, Outcome.NOT_APPLICABLE),
    "Half End": (EventType.PERIOD_END, Outcome.NOT_APPLICABLE),
}

# Flags copied into provider_qualifiers when present (StatsBomb-specific).
QUALIFIER_FLAGS = ("counterpress", "off_camera", "out")


@dataclass
class EventMappingResult:
    events: list[Event] = field(default_factory=list)
    period_lengths_s: dict[int, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def parse_timestamp(value: str) -> float:
    """'HH:MM:SS.mmm' -> seconds."""
    hours, minutes, seconds = value.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def event_id(provider_event_id: str) -> str:
    return internal_id(PROVIDER, EntityType.EVENT, provider_event_id)


def _name(obj: Any) -> str | None:
    return obj.get("name") if isinstance(obj, dict) else None


class _EventMapper:
    def __init__(self, match_id: str, source_release: str, ingestion_run_id: str) -> None:
        self.match_id = match_id
        self.source_release = source_release
        self.ingestion_run_id = ingestion_run_id
        self.result = EventMappingResult()
        self._handlers: dict[str, Callable[[RawEvent], dict[str, Any]]] = {
            "Pass": self._pass,
            "Ball Receipt*": self._ball_receipt,
            "Carry": self._carry,
            "Pressure": lambda raw: {"type": EventType.PRESSURE, "outcome": Outcome.NOT_APPLICABLE},
            "Dribble": self._dribble,
            "Duel": self._duel,
            "50/50": self._fifty_fifty,
            "Interception": self._interception,
            "Clearance": self._clearance,
            "Block": self._block,
            "Ball Recovery": self._ball_recovery,
            "Miscontrol": self._miscontrol,
            "Shot": self._shot,
            "Goal Keeper": self._goalkeeper,
            "Foul Committed": self._foul_committed,
            "Bad Behaviour": self._bad_behaviour,
            "Substitution": self._substitution,
        }

    # -- helpers -----------------------------------------------------------

    def _warn(self, raw: RawEvent, message: str) -> None:
        self.result.warnings.append(f"event {raw.get('id')}: {message}")

    def _lookup(self, table: dict[Any, Any], key: Any, raw: RawEvent, what: str, default: Any = None) -> Any:
        if key in table:
            return table[key]
        if key is not None:
            self._warn(raw, f"unmapped {what} {key!r}")
        return default

    def _body_part(self, detail: dict[str, Any], raw: RawEvent) -> BodyPart | None:
        return self._lookup(BODY_PART, _name(detail.get("body_part")), raw, "body part")

    def _set_piece(self, type_name: str | None, raw: RawEvent) -> SetPiece | None:
        if type_name is None or type_name in OPEN_PLAY_TYPES:
            return None
        return self._lookup(SET_PIECE, type_name, raw, "set piece type")

    # -- per-type handlers: return Event kwargs ------------------------------

    def _pass(self, raw: RawEvent) -> dict[str, Any]:
        detail = raw["pass"]
        technique = _name(detail.get("technique"))
        recipient = detail.get("recipient")
        assisted = detail.get("assisted_shot_id")
        return {
            "type": EventType.PASS,
            "outcome": self._lookup(PASS_OUTCOME, _name(detail.get("outcome")), raw, "pass outcome", Outcome.UNKNOWN),
            "end": to_canonical_point(detail.get("end_location")),
            "body_part": self._body_part(detail, raw),
            "set_piece": self._set_piece(_name(detail.get("type")), raw),
            "aerial_won": bool(detail.get("aerial_won", False)),
            "pass_detail": PassDetail(
                height=self._lookup(PASS_HEIGHT, _name(detail.get("height")), raw, "pass height"),
                recipient_id=internal_id(PROVIDER, EntityType.PLAYER, recipient["id"]) if recipient else None,
                is_cross=bool(detail.get("cross", False)),
                is_switch=bool(detail.get("switch", False)),
                is_cut_back=bool(detail.get("cut_back", False)),
                is_through_ball=bool(detail.get("through_ball", False)) or technique == "Through Ball",
                is_shot_assist=bool(detail.get("shot_assist", False)),
                is_goal_assist=bool(detail.get("goal_assist", False)),
                assisted_shot_event_id=event_id(assisted) if assisted else None,
            ),
        }

    def _ball_receipt(self, raw: RawEvent) -> dict[str, Any]:
        outcome_name = _name(raw.get("ball_receipt", {}).get("outcome"))
        table = {None: Outcome.SUCCESS, "Incomplete": Outcome.FAIL}
        return {
            "type": EventType.BALL_RECEIPT,
            "outcome": self._lookup(table, outcome_name, raw, "ball receipt outcome", Outcome.UNKNOWN),
        }

    def _carry(self, raw: RawEvent) -> dict[str, Any]:
        return {
            "type": EventType.CARRY,
            "outcome": Outcome.NOT_APPLICABLE,
            "end": to_canonical_point(raw["carry"].get("end_location")),
        }

    def _dribble(self, raw: RawEvent) -> dict[str, Any]:
        table = {"Complete": Outcome.SUCCESS, "Incomplete": Outcome.FAIL}
        return {
            "type": EventType.TAKE_ON,
            "outcome": self._lookup(table, _name(raw["dribble"].get("outcome")), raw, "dribble outcome", Outcome.UNKNOWN),
        }

    def _duel(self, raw: RawEvent) -> dict[str, Any]:
        detail = raw["duel"]
        duel_type = _name(detail.get("type"))
        if duel_type == "Aerial Lost":
            return {"type": EventType.DUEL, "duel_kind": DuelKind.AERIAL, "outcome": Outcome.FAIL}
        if duel_type == "Tackle":
            outcome = self._lookup(CONTEST_OUTCOME, _name(detail.get("outcome")), raw, "duel outcome", Outcome.UNKNOWN)
            return {"type": EventType.DUEL, "duel_kind": DuelKind.GROUND, "outcome": outcome}
        self._warn(raw, f"unmapped duel type {duel_type!r}")
        return {"type": EventType.OTHER, "outcome": Outcome.UNKNOWN}

    def _fifty_fifty(self, raw: RawEvent) -> dict[str, Any]:
        outcome_name = _name(raw.get("50_50", {}).get("outcome"))
        return {
            "type": EventType.DUEL,
            "duel_kind": DuelKind.LOOSE_BALL,
            "outcome": self._lookup(FIFTY_FIFTY_OUTCOME, outcome_name, raw, "50/50 outcome", Outcome.UNKNOWN),
        }

    def _interception(self, raw: RawEvent) -> dict[str, Any]:
        outcome_name = _name(raw["interception"].get("outcome"))
        return {
            "type": EventType.INTERCEPTION,
            "outcome": self._lookup(CONTEST_OUTCOME, outcome_name, raw, "interception outcome", Outcome.UNKNOWN),
        }

    def _clearance(self, raw: RawEvent) -> dict[str, Any]:
        detail = raw.get("clearance", {})
        return {
            "type": EventType.CLEARANCE,
            "outcome": Outcome.SUCCESS,
            "body_part": self._body_part(detail, raw),
            "aerial_won": bool(detail.get("aerial_won", False)),
        }

    def _block(self, raw: RawEvent) -> dict[str, Any]:
        detail = raw.get("block", {})
        qualifiers = {key: True for key in ("save_block", "deflection", "offensive") if detail.get(key)}
        return {"type": EventType.BLOCK, "outcome": Outcome.SUCCESS, "_qualifiers": qualifiers}

    def _ball_recovery(self, raw: RawEvent) -> dict[str, Any]:
        failed = raw.get("ball_recovery", {}).get("recovery_failure", False)
        return {"type": EventType.BALL_RECOVERY, "outcome": Outcome.FAIL if failed else Outcome.SUCCESS}

    def _miscontrol(self, raw: RawEvent) -> dict[str, Any]:
        return {
            "type": EventType.MISCONTROL,
            "outcome": Outcome.FAIL,
            "aerial_won": bool(raw.get("miscontrol", {}).get("aerial_won", False)),
        }

    def _shot(self, raw: RawEvent) -> dict[str, Any]:
        detail = raw["shot"]
        outcome_name = _name(detail.get("outcome"))
        shot_outcome = SHOT_OUTCOME.get(outcome_name)
        if shot_outcome is None:
            raise ValueError(f"event {raw['id']}: unmapped shot outcome {outcome_name!r}")
        end_location = detail.get("end_location")
        key_pass = detail.get("key_pass_id")
        metrics: tuple[ProviderMetric, ...] = ()
        if detail.get("statsbomb_xg") is not None:
            metrics = (ProviderMetric("xg", float(detail["statsbomb_xg"]), PROVIDER, XG_MODEL_VERSION),)
        return {
            "type": EventType.SHOT,
            "outcome": Outcome.SUCCESS if shot_outcome is ShotOutcome.GOAL else Outcome.FAIL,
            "end": to_canonical_point(end_location),
            "body_part": self._body_part(detail, raw),
            "set_piece": self._set_piece(_name(detail.get("type")), raw),
            "aerial_won": bool(detail.get("aerial_won", False)),
            "provider_metrics": metrics,
            "shot_detail": ShotDetail(
                outcome=shot_outcome,
                technique=_name(detail.get("technique")),
                is_first_time=bool(detail.get("first_time", False)),
                key_pass_event_id=event_id(key_pass) if key_pass else None,
                end_z=float(end_location[2]) if end_location and len(end_location) > 2 else None,
            ),
            "_qualifiers": {"shot_outcome_raw": outcome_name},
        }

    def _goalkeeper(self, raw: RawEvent) -> dict[str, Any]:
        detail = raw.get("goalkeeper", {})
        kind = self._lookup(GOALKEEPER_KIND, _name(detail.get("type")), raw, "goalkeeper type", GoalkeeperActionKind.OTHER)
        outcome_name = _name(detail.get("outcome"))
        outcome = GOALKEEPER_OUTCOME.get(outcome_name, Outcome.UNKNOWN)
        return {
            "type": EventType.GOALKEEPER_ACTION,
            "outcome": outcome,
            "goalkeeper_action_kind": kind,
            "body_part": self._body_part(detail, raw),
            "end": to_canonical_point(detail.get("end_location")),
        }

    def _foul_committed(self, raw: RawEvent) -> dict[str, Any]:
        detail = raw.get("foul_committed", {})
        qualifiers = {key: True for key in ("penalty", "advantage", "offensive") if detail.get(key)}
        return {"type": EventType.FOUL_COMMITTED, "outcome": Outcome.NOT_APPLICABLE, "_qualifiers": qualifiers}

    def _bad_behaviour(self, raw: RawEvent) -> dict[str, Any]:
        card_name = _name(raw.get("bad_behaviour", {}).get("card"))
        card = self._lookup(CARD_TYPE, card_name, raw, "card type")
        if card is None:
            return {"type": EventType.OTHER, "outcome": Outcome.NOT_APPLICABLE}
        return {"type": EventType.CARD, "outcome": Outcome.NOT_APPLICABLE, "card_type": card}

    def _substitution(self, raw: RawEvent) -> dict[str, Any]:
        detail = raw["substitution"]
        return {
            "type": EventType.SUBSTITUTION,
            "outcome": Outcome.NOT_APPLICABLE,
            "substitute_player_id": internal_id(PROVIDER, EntityType.PLAYER, detail["replacement"]["id"]),
            "_qualifiers": {"reason": _name(detail.get("outcome"))},
        }

    # -- main --------------------------------------------------------------

    def _build(self, raw: RawEvent, provider_event_id: str, mapped: dict[str, Any]) -> Event:
        qualifiers = {flag: True for flag in QUALIFIER_FLAGS if raw.get(flag)}
        qualifiers.update(mapped.pop("_qualifiers", {}))
        player = raw.get("player")
        return Event(
            id=event_id(provider_event_id),
            match_id=self.match_id,
            period=raw["period"],
            time_s=parse_timestamp(raw["timestamp"]),
            team_id=internal_id(PROVIDER, EntityType.TEAM, raw["team"]["id"]),
            player_id=internal_id(PROVIDER, EntityType.PLAYER, player["id"]) if player else None,
            start=to_canonical_point(raw.get("location")),
            possession_origin=self._lookup(POSSESSION_ORIGIN, _name(raw.get("play_pattern")), raw, "play pattern"),
            possession_id=str(raw["possession"]) if "possession" in raw else None,
            under_pressure=bool(raw.get("under_pressure", False)),
            related_event_ids=tuple(event_id(rid) for rid in raw.get("related_events", ())),
            provider_event_type=raw["type"]["name"],
            provider_qualifiers=qualifiers,
            provenance=Provenance(PROVIDER, provider_event_id, self.source_release, self.ingestion_run_id),
            **mapped,
        )

    def map_event(self, raw: RawEvent) -> None:
        type_name = raw["type"]["name"]
        if type_name == "Half End":
            period = raw["period"]
            length = parse_timestamp(raw["timestamp"])
            self.result.period_lengths_s[period] = max(length, self.result.period_lengths_s.get(period, 0.0))

        if type_name in SIMPLE_TYPES:
            event_type, outcome = SIMPLE_TYPES[type_name]
            mapped: dict[str, Any] = {"type": event_type, "outcome": outcome}
        elif type_name in self._handlers:
            mapped = self._handlers[type_name](raw)
        else:
            # Own Goal For, Starting XI, Tactical Shift, Offside, Shield, Error, ...
            mapped = {"type": EventType.OTHER, "outcome": Outcome.NOT_APPLICABLE}
        self.result.events.append(self._build(raw, raw["id"], mapped))

        card_name = _name(raw.get("foul_committed", {}).get("card")) if type_name == "Foul Committed" else None
        if card_name is not None:
            card = self._lookup(CARD_TYPE, card_name, raw, "card type")
            if card is not None:
                card_event = {"type": EventType.CARD, "outcome": Outcome.NOT_APPLICABLE, "card_type": card}
                self.result.events.append(self._build(raw, f"{raw['id']}:card", card_event))


def map_events(
    raw_events: list[RawEvent], match_id: str, source_release: str, ingestion_run_id: str
) -> EventMappingResult:
    mapper = _EventMapper(match_id, source_release, ingestion_run_id)
    for raw in raw_events:
        mapper.map_event(raw)
    return mapper.result
