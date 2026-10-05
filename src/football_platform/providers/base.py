"""Provider adapter contract (docs/ARCHITECTURE.md §3).

Adapters read from the local raw store only, map provider data to canonical
objects, and declare their capabilities. Analytics never imports this package.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from football_platform.canonical.capabilities import (  # noqa: F401  (re-exported for adapters)
    PositionGranularity,
    ProviderCapabilities,
    TimePrecision,
)
from football_platform.canonical.models import (
    Appearance,
    Competition,
    Event,
    ExternalId,
    Match,
    Player,
    Season,
    Team,
)


@dataclass(frozen=True, slots=True)
class SeasonEntry:
    competition: Competition
    season: Season
    external_ids: tuple[ExternalId, ...]


@dataclass(frozen=True, slots=True)
class MatchEntry:
    match: Match
    home_team: Team
    away_team: Team
    external_ids: tuple[ExternalId, ...]


@dataclass(frozen=True, slots=True)
class MatchBundle:
    """Everything an adapter produces for one match."""

    match: Match
    players: tuple[Player, ...]
    appearances: tuple[Appearance, ...]
    events: tuple[Event, ...]
    external_ids: tuple[ExternalId, ...]
    warnings: tuple[str, ...] = field(default=())


class ProviderAdapter(Protocol):
    def capabilities(self) -> ProviderCapabilities: ...

    def list_seasons(self) -> list[SeasonEntry]: ...

    def list_matches(self, season: Season) -> list[MatchEntry]: ...

    def load_match(self, match: Match) -> MatchBundle: ...
