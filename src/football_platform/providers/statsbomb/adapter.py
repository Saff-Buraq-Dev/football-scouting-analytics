"""StatsBomb Open Data adapter: the only place that understands StatsBomb's schema."""

from __future__ import annotations

import json
from datetime import date, time
from importlib import resources
from typing import Any

from football_platform.canonical.enums import (
    CompetitionType,
    CoverageScope,
    EntityType,
    Gender,
    MatchStatus,
    TeamType,
)
from football_platform.canonical.identifiers import internal_id
from football_platform.canonical.models import Competition, ExternalId, Match, Season, Team
from football_platform.providers.base import (
    MatchBundle,
    MatchEntry,
    PositionGranularity,
    ProviderCapabilities,
    SeasonEntry,
    TimePrecision,
)
from football_platform.providers.statsbomb.constants import PROVIDER
from football_platform.providers.statsbomb.events import map_events
from football_platform.providers.statsbomb.lineups import exit_times_from_events, map_lineups
from football_platform.providers.statsbomb.raw_store import StatsBombRawStore

# StatsBomb does not label competition formats. Non-international competitions
# listed here are knockout cups; all other non-international ones are leagues.
CUP_COMPETITIONS = {"Champions League", "Copa del Rey", "UEFA Europa League"}

CAPABILITIES = ProviderCapabilities(
    provider=PROVIDER,
    source_coordinate_system="statsbomb_120x80_y_down",
    has_event_end_locations=True,
    has_provider_xg=True,
    has_pressure_events=True,
    has_carries=True,
    has_ball_receipts=True,
    has_freeze_frames=False,  # 360 data is not ingested yet (Phase 9)
    has_possession_ids=True,
    has_player_birth_date=False,
    has_position_spells=True,
    position_granularity=PositionGranularity.SLOT,
    minutes_precision=TimePrecision.SECOND,
)


def load_coverage_review() -> dict[tuple[int, int], dict[str, Any]]:
    """Reviewed coverage classification (decision D010, docs/data/STATSBOMB_COVERAGE.md)."""
    text = resources.files(__package__).joinpath("coverage_review.json").read_text(encoding="utf-8")
    return {(s["competition_id"], s["season_id"]): s for s in json.loads(text)["seasons"]}


def _external(entity: EntityType, iid: str, provider_id: Any) -> ExternalId:
    return ExternalId(entity, iid, PROVIDER, str(provider_id))


class StatsBombOpenDataAdapter:
    def __init__(self, store: StatsBombRawStore, ingestion_run_id: str) -> None:
        self.store = store
        self.ingestion_run_id = ingestion_run_id
        self._coverage = load_coverage_review()
        # Canonical ids -> StatsBomb ids, filled while listing.
        self._season_refs: dict[str, tuple[int, int]] = {}
        self._season_international: dict[str, bool] = {}
        self._match_refs: dict[str, int] = {}

    def capabilities(self) -> ProviderCapabilities:
        return CAPABILITIES

    # -- competitions & seasons ---------------------------------------------

    def list_seasons(self) -> list[SeasonEntry]:
        entries = []
        for raw in self.store.competitions():
            cid, sid = raw["competition_id"], raw["season_id"]
            competition_id = internal_id(PROVIDER, EntityType.COMPETITION, cid)
            # StatsBomb season ids are shared across competitions (27 = 2015/16 everywhere).
            season_id = internal_id(PROVIDER, EntityType.SEASON, f"{cid}:{sid}")
            international = bool(raw["competition_international"])
            if international:
                competition_type = CompetitionType.INTERNATIONAL_TOURNAMENT
            elif raw["competition_name"] in CUP_COMPETITIONS:
                competition_type = CompetitionType.CUP
            else:
                competition_type = CompetitionType.LEAGUE
            review = self._coverage.get((cid, sid))
            competition = Competition(
                id=competition_id,
                name=raw["competition_name"],
                area=raw["country_name"],
                gender=Gender(raw["competition_gender"]),
                competition_type=competition_type,
                is_youth=bool(raw.get("competition_youth", False)),
            )
            season = Season(
                id=season_id,
                competition_id=competition_id,
                label=raw["season_name"],
                coverage_scope=CoverageScope(review["coverage_scope"]) if review else CoverageScope.UNKNOWN,
                coverage_note=review.get("coverage_note") if review else "Not reviewed",
                has_events=True,
                has_lineups=True,
                has_freeze_frames=raw.get("match_available_360") is not None,
            )
            self._season_refs[season_id] = (cid, sid)
            self._season_international[season_id] = international
            entries.append(
                SeasonEntry(
                    competition,
                    season,
                    (
                        _external(EntityType.COMPETITION, competition_id, cid),
                        _external(EntityType.SEASON, season_id, f"{cid}:{sid}"),
                    ),
                )
            )
        return entries

    # -- matches -------------------------------------------------------------

    def _team(self, raw_team: dict[str, Any], side: str, international: bool) -> Team:
        country = raw_team.get("country")
        return Team(
            id=internal_id(PROVIDER, EntityType.TEAM, raw_team[f"{side}_team_id"]),
            name=raw_team[f"{side}_team_name"],
            team_type=TeamType.NATIONAL if international else TeamType.CLUB,
            gender=Gender(raw_team[f"{side}_team_gender"]),
            area=country.get("name") if country else None,
        )

    def list_matches(self, season: Season) -> list[MatchEntry]:
        if season.id not in self._season_refs:
            raise KeyError(f"Season {season.id} was not listed by this adapter")
        cid, sid = self._season_refs[season.id]
        international = self._season_international[season.id]
        entries = []
        for raw in self.store.matches(cid, sid):
            match_id = internal_id(PROVIDER, EntityType.MATCH, raw["match_id"])
            home = self._team(raw["home_team"], "home", international)
            away = self._team(raw["away_team"], "away", international)
            kickoff = raw.get("kick_off")
            match = Match(
                id=match_id,
                season_id=season.id,
                competition_id=season.competition_id,
                match_date=date.fromisoformat(raw["match_date"]),
                kickoff_time=time.fromisoformat(kickoff) if kickoff else None,
                home_team_id=home.id,
                away_team_id=away.id,
                home_score=raw["home_score"],
                away_score=raw["away_score"],
                status=MatchStatus.PLAYED,
                stage=(raw.get("competition_stage") or {}).get("name"),
                matchweek=raw.get("match_week"),
                venue=(raw.get("stadium") or {}).get("name"),
                referee=(raw.get("referee") or {}).get("name"),
            )
            self._match_refs[match_id] = raw["match_id"]
            entries.append(
                MatchEntry(
                    match,
                    home,
                    away,
                    (
                        _external(EntityType.MATCH, match_id, raw["match_id"]),
                        _external(EntityType.TEAM, home.id, raw["home_team"]["home_team_id"]),
                        _external(EntityType.TEAM, away.id, raw["away_team"]["away_team_id"]),
                    ),
                )
            )
        return entries

    # -- match content -------------------------------------------------------

    def load_match(self, match: Match) -> MatchBundle:
        if match.id not in self._match_refs:
            raise KeyError(f"Match {match.id} was not listed by this adapter")
        provider_match_id = self._match_refs[match.id]
        raw_events = self.store.events(provider_match_id)
        event_result = map_events(raw_events, match.id, self.store.commit, self.ingestion_run_id)
        raw_lineups = self.store.lineups(provider_match_id)
        lineup_result = map_lineups(
            raw_lineups, match.id, event_result.period_lengths_s, exit_times_from_events(raw_events)
        )
        external_ids = [
            _external(EntityType.PLAYER, internal_id(PROVIDER, EntityType.PLAYER, p["player_id"]), p["player_id"])
            for team in raw_lineups
            for p in team["lineup"]
        ]
        return MatchBundle(
            match=match,
            players=tuple(lineup_result.players),
            appearances=tuple(lineup_result.appearances),
            events=tuple(event_result.events),
            external_ids=tuple(external_ids),
            warnings=tuple(event_result.warnings + lineup_result.warnings),
        )
