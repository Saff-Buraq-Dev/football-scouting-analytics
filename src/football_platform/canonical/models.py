"""Canonical football data model v1.1 (docs/ARCHITECTURE.md §5, decision D012).

Provider-independent. Nothing here may reference a specific provider's schema.
Optional fields are None when the source does not provide them; analytics must
treat None as "unavailable", never as zero.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time

from football_platform.canonical.enums import (
    BodyPart,
    CardType,
    CompetitionType,
    CoverageScope,
    DuelKind,
    EntityType,
    EventType,
    Gender,
    GoalkeeperActionKind,
    MatchStatus,
    Outcome,
    PassHeight,
    PositionLine,
    PositionRole,
    PossessionOrigin,
    SetPiece,
    ShotOutcome,
    Side,
    TeamType,
)
from football_platform.canonical.pitch import Point

PERIODS = (1, 2, 3, 4, 5)  # 3-4 extra time, 5 penalty shoot-out
SHOOTOUT_PERIOD = 5


@dataclass(frozen=True, slots=True)
class Provenance:
    source_provider: str
    source_record_id: str
    source_release: str
    ingestion_run_id: str


@dataclass(frozen=True, slots=True)
class ExternalId:
    entity_type: EntityType
    internal_id: str
    provider: str
    provider_id: str


@dataclass(frozen=True, slots=True)
class ProviderMetric:
    """A value computed by a provider's own model (decision D007), e.g. xG."""

    metric_key: str
    value: float
    source_provider: str
    model_version: str


@dataclass(frozen=True, slots=True)
class Competition:
    id: str
    name: str
    area: str
    gender: Gender
    competition_type: CompetitionType
    is_youth: bool | None = None
    tier: int | None = None


@dataclass(frozen=True, slots=True)
class Season:
    id: str
    competition_id: str
    label: str
    coverage_scope: CoverageScope
    has_events: bool
    has_lineups: bool
    has_freeze_frames: bool
    coverage_note: str | None = None
    start_date: date | None = None
    end_date: date | None = None


@dataclass(frozen=True, slots=True)
class Team:
    id: str
    name: str
    team_type: TeamType
    gender: Gender
    area: str | None = None
    short_name: str | None = None


@dataclass(frozen=True, slots=True)
class Player:
    id: str
    name: str
    known_name: str | None = None
    nationality: str | None = None
    birth_date: date | None = None
    height_cm: float | None = None
    preferred_foot: str | None = None


@dataclass(frozen=True, slots=True)
class Match:
    id: str
    season_id: str
    competition_id: str
    match_date: date
    home_team_id: str
    away_team_id: str
    home_score: int
    away_score: int
    status: MatchStatus
    # Local kick-off time as given by the source; the time zone is not guaranteed.
    kickoff_time: time | None = None
    stage: str | None = None
    matchweek: int | None = None
    venue: str | None = None
    referee: str | None = None

    def __post_init__(self) -> None:
        if self.home_team_id == self.away_team_id:
            raise ValueError(f"Match {self.id}: home and away team are identical")
        if self.home_score < 0 or self.away_score < 0:
            raise ValueError(f"Match {self.id}: negative score")


@dataclass(frozen=True, slots=True)
class Position:
    """(line, role, side). Providers with line-only granularity leave role/side None."""

    line: PositionLine
    role: PositionRole | None = None
    side: Side | None = None


@dataclass(frozen=True, slots=True)
class PositionSpell:
    """Time a player spent in one position within ONE period (seconds since period start)."""

    position: Position
    period: int
    start_s: float
    end_s: float

    def __post_init__(self) -> None:
        if self.period not in PERIODS:
            raise ValueError(f"Invalid period {self.period}")
        if self.start_s < 0 or self.end_s < self.start_s:
            raise ValueError(f"Invalid spell interval {self.start_s}-{self.end_s}")

    @property
    def duration_s(self) -> float:
        return self.end_s - self.start_s


@dataclass(frozen=True, slots=True)
class Appearance:
    """A player's participation in a match. Unused substitutes have no spells."""

    match_id: str
    team_id: str
    player_id: str
    is_starter: bool
    position_spells: tuple[PositionSpell, ...]
    shirt_number: int | None = None

    @property
    def played(self) -> bool:
        return any(spell.duration_s > 0 for spell in self.position_spells)

    @property
    def minutes_played(self) -> float:
        """Minutes on the pitch, excluding the penalty shoot-out.

        Method documented in docs/FOOTBALL_ANALYTICS.md ("Minutes played").
        """
        seconds = sum(
            spell.duration_s for spell in self.position_spells if spell.period != SHOOTOUT_PERIOD
        )
        return seconds / 60.0


@dataclass(frozen=True, slots=True)
class PassDetail:
    height: PassHeight | None = None
    recipient_id: str | None = None
    is_cross: bool = False
    is_switch: bool = False
    is_cut_back: bool = False
    is_through_ball: bool = False
    is_shot_assist: bool = False
    is_goal_assist: bool = False
    assisted_shot_event_id: str | None = None


@dataclass(frozen=True, slots=True)
class ShotDetail:
    outcome: ShotOutcome
    technique: str | None = None
    is_first_time: bool = False
    key_pass_event_id: str | None = None
    end_z: float | None = None  # height at the goal line, in source units


@dataclass(frozen=True, slots=True)
class Event:
    id: str
    match_id: str
    period: int
    time_s: float
    team_id: str
    type: EventType
    outcome: Outcome
    provenance: Provenance
    player_id: str | None = None
    start: Point | None = None
    end: Point | None = None
    body_part: BodyPart | None = None
    set_piece: SetPiece | None = None
    possession_origin: PossessionOrigin | None = None
    possession_id: str | None = None
    duel_kind: DuelKind | None = None
    aerial_won: bool | None = None
    under_pressure: bool | None = None
    related_event_ids: tuple[str, ...] = ()
    pass_detail: PassDetail | None = None
    shot_detail: ShotDetail | None = None
    goalkeeper_action_kind: GoalkeeperActionKind | None = None
    card_type: CardType | None = None
    substitute_player_id: str | None = None
    provider_metrics: tuple[ProviderMetric, ...] = ()
    provider_event_type: str | None = None
    provider_qualifiers: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.period not in PERIODS:
            raise ValueError(f"Event {self.id}: invalid period {self.period}")
        if self.time_s < 0:
            raise ValueError(f"Event {self.id}: negative time")
        if self.type is EventType.DUEL and self.duel_kind is None:
            raise ValueError(f"Event {self.id}: duel without duel_kind")
        if self.type is EventType.SHOT and self.shot_detail is None:
            raise ValueError(f"Event {self.id}: shot without shot_detail")
        if self.type is EventType.CARD and self.card_type is None:
            raise ValueError(f"Event {self.id}: card without card_type")
