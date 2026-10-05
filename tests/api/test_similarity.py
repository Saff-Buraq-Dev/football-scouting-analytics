import pytest

from football_platform.api.similarity import SimilarityUnavailableError, build_similarity

FEATURES = ["tackles", "interceptions", "progressive_passes"]


def rows(key, values, eligible=True):
    player, season = key.split(":")
    return [{"player_id": player, "season_id": season, "player_name": player.upper(), "teams": ["T"],
             "competition": "Premier League", "minutes": 2000.0, "eligible": eligible,
             "team_possession_pct": 50.0, "metric_key": f, "regressed": v} for f, v in zip(FEATURES, values)]


POPULATION = (rows("a:s", [4.0, 3.0, 3.0]) + rows("b:s", [3.9, 2.9, 3.2]) + rows("c:s", [1.0, 0.5, 10.0])
              + rows("d:s", [2.0, 1.5, 6.0]))


def test_nearest_players_come_first_with_population_based_similarity():
    result = build_similarity(POPULATION, FEATURES, "a:s", limit=3)
    assert [r["player_id"] for r in result["results"]] == ["b", "d", "c"]
    assert result["population_size"] == 3  # the target is not its own neighbour
    assert result["results"][0]["similarity_percentile"] == pytest.approx(200 / 3)  # 2 of 3 are farther
    assert result["results"][0]["main_differences"][0]["key"] in FEATURES


def test_target_below_threshold_is_compared_to_the_eligible_population():
    data = POPULATION + rows("short:s", [3.95, 2.95, 3.1], eligible=False)
    result = build_similarity(data, FEATURES, "short:s", limit=2)
    assert {r["player_id"] for r in result["results"]} == {"a", "b"}


def test_target_without_profile_is_rejected():
    with pytest.raises(SimilarityUnavailableError):
        build_similarity(POPULATION, FEATURES, "missing:s", limit=3)
