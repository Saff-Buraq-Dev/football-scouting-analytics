"""Canonical vocabularies. See docs/ARCHITECTURE.md §4.3 and §5 for definitions."""

from enum import StrEnum


class Gender(StrEnum):
    MALE = "male"
    FEMALE = "female"


class CompetitionType(StrEnum):
    LEAGUE = "league"
    CUP = "cup"
    INTERNATIONAL_TOURNAMENT = "international_tournament"


class TeamType(StrEnum):
    CLUB = "club"
    NATIONAL = "national"


class CoverageScope(StrEnum):
    """Whether a season's matches form a complete population (decision D010).

    UNKNOWN is the safe default: population metrics treat it like PARTIAL.
    """

    COMPLETE = "complete"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class MatchStatus(StrEnum):
    PLAYED = "played"
    SCHEDULED = "scheduled"
    ABANDONED = "abandoned"


class EventType(StrEnum):
    PASS = "pass"
    SHOT = "shot"
    OWN_GOAL = "own_goal"
    CARRY = "carry"  # capability-gated: has_carries
    BALL_RECEIPT = "ball_receipt"  # capability-gated: has_ball_receipts
    PRESSURE = "pressure"  # capability-gated: has_pressure_events
    TAKE_ON = "take_on"
    DRIBBLED_PAST = "dribbled_past"
    DUEL = "duel"
    INTERCEPTION = "interception"
    CLEARANCE = "clearance"
    BLOCK = "block"
    BALL_RECOVERY = "ball_recovery"
    MISCONTROL = "miscontrol"
    DISPOSSESSED = "dispossessed"
    FOUL_COMMITTED = "foul_committed"
    FOUL_WON = "foul_won"
    GOALKEEPER_ACTION = "goalkeeper_action"
    CARD = "card"
    SUBSTITUTION = "substitution"
    PERIOD_START = "period_start"
    PERIOD_END = "period_end"
    OTHER = "other"


class Outcome(StrEnum):
    SUCCESS = "success"
    FAIL = "fail"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class DuelKind(StrEnum):
    GROUND = "ground"
    AERIAL = "aerial"
    LOOSE_BALL = "loose_ball"


class SetPiece(StrEnum):
    """The action itself restarts play. Absent (None) means open play."""

    CORNER = "corner"
    FREE_KICK = "free_kick"
    THROW_IN = "throw_in"
    PENALTY = "penalty"
    GOAL_KICK = "goal_kick"
    KICK_OFF = "kick_off"


class PossessionOrigin(StrEnum):
    """How the possession containing the event began."""

    REGULAR_PLAY = "regular_play"
    THROW_IN = "throw_in"
    FREE_KICK = "free_kick"
    GOAL_KICK = "goal_kick"
    KICK_OFF = "kick_off"
    CORNER = "corner"
    KEEPER = "keeper"
    COUNTER = "counter"
    OTHER = "other"


class BodyPart(StrEnum):
    FOOT_LEFT = "foot_left"
    FOOT_RIGHT = "foot_right"
    HEAD = "head"
    HANDS = "hands"
    OTHER = "other"


class PassHeight(StrEnum):
    GROUND = "ground"
    LOW = "low"
    HIGH = "high"


class ShotOutcome(StrEnum):
    GOAL = "goal"
    SAVED = "saved"
    BLOCKED = "blocked"
    OFF_TARGET = "off_target"
    POST = "post"
    WAYWARD = "wayward"


class GoalkeeperActionKind(StrEnum):
    SHOT_FACED = "shot_faced"
    SAVE = "save"
    GOAL_CONCEDED = "goal_conceded"
    CLAIM = "claim"
    PUNCH = "punch"
    SWEEPER = "sweeper"
    SMOTHER = "smother"
    OTHER = "other"


class CardType(StrEnum):
    YELLOW = "yellow"
    SECOND_YELLOW = "second_yellow"
    RED = "red"


class PositionLine(StrEnum):
    GK = "GK"
    DEF = "DEF"
    MID = "MID"
    FWD = "FWD"


class PositionRole(StrEnum):
    GK = "GK"
    CB = "CB"
    FB = "FB"
    WB = "WB"
    DM = "DM"
    CM = "CM"
    WM = "WM"
    AM = "AM"
    W = "W"
    CF = "CF"


class Side(StrEnum):
    LEFT = "L"
    CENTRE = "C"
    RIGHT = "R"


class EntityType(StrEnum):
    COMPETITION = "competition"
    SEASON = "season"
    TEAM = "team"
    PLAYER = "player"
    MATCH = "match"
    EVENT = "event"
