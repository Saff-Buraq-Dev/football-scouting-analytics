import pytest

from football_platform.canonical.enums import CompetitionType, CoverageScope, EventType, TeamType
from football_platform.providers.statsbomb.adapter import StatsBombOpenDataAdapter
from football_platform.providers.statsbomb.raw_store import RawFileMissingError, StatsBombRawStore
from tests.providers.statsbomb.factories import write_synthetic_raw_store

COMMIT = "testcommit"


@pytest.fixture
def adapter(tmp_path):
    write_synthetic_raw_store(tmp_path, COMMIT)
    return StatsBombOpenDataAdapter(StatsBombRawStore(tmp_path, COMMIT), ingestion_run_id="run-1")


def test_seasons_get_reviewed_coverage_or_unknown(adapter):
    entries = {e.competition.name: e for e in adapter.list_seasons()}
    assert entries["Premier League"].season.coverage_scope is CoverageScope.COMPLETE
    assert entries["Test Cup"].season.coverage_scope is CoverageScope.UNKNOWN
    assert entries["Premier League"].competition.competition_type is CompetitionType.LEAGUE


def test_shared_statsbomb_season_ids_give_distinct_canonical_seasons(adapter):
    entries = {e.competition.name: e for e in adapter.list_seasons()}
    assert entries["Premier League"].season.id != entries["La Liga"].season.id


def test_end_to_end_match(adapter):
    season = next(e.season for e in adapter.list_seasons() if e.competition.name == "Premier League")
    (entry,) = adapter.list_matches(season)
    assert entry.home_team.team_type is TeamType.CLUB
    assert (entry.match.home_score, entry.match.away_score) == (1, 0)

    bundle = adapter.load_match(entry.match)
    shots = [e for e in bundle.events if e.type is EventType.SHOT]
    assert len(shots) == 1 and shots[0].team_id == entry.home_team.id
    starter = next(a for a in bundle.appearances if a.is_starter)
    assert starter.minutes_played == pytest.approx(94)
    unused = next(a for a in bundle.appearances if not a.is_starter)
    assert not unused.played
    assert {x.provider_id for x in bundle.external_ids} == {"1", "2"}
    assert all(e.provenance.source_release == COMMIT for e in bundle.events)


def test_missing_raw_file_raises_clear_error(adapter):
    season = next(e.season for e in adapter.list_seasons() if e.competition.name == "La Liga")
    with pytest.raises(RawFileMissingError):
        adapter.list_matches(season)


def test_capabilities_declare_statsbomb_specific_concepts(adapter):
    caps = adapter.capabilities()
    assert caps.has_pressure_events and caps.has_carries and caps.has_provider_xg
    assert not caps.has_player_birth_date
