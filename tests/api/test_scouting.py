import pytest

from football_platform.analytics.definitions import PositionGroup
from football_platform.api.scouting import InvalidCriteriaError, build_scouting_result, parse_criteria, presets_payload


def test_criteria_are_parsed_and_validated_for_the_group():
    criteria = parse_criteria(["tackles:70", "interceptions:60"], PositionGroup.CENTRAL_MIDFIELD)
    assert [(c.metric_key, c.min_percentile) for c in criteria] == [("tackles", 70), ("interceptions", 60)]


@pytest.mark.parametrize("raw", [
    ["unknown_metric:50"],               # unknown metric
    ["gk_np_save_pct:50"],               # goalkeeper metric for an outfield group
    ["tackles:abc"],                     # not a number
    ["tackles:120"],                     # outside 0-100
    ["tackles:50", "tackles:60"],        # duplicate
    [],                                  # none
])
def test_invalid_criteria_are_rejected(raw):
    with pytest.raises(InvalidCriteriaError):
        parse_criteria(raw, PositionGroup.CENTRAL_MIDFIELD)


def row(player, metric, percentile):
    return {"player_id": player, "season_id": "s1", "player_name": player.upper(), "teams": ["T"],
            "competition": "Premier League", "season_label": "2015/2016", "minutes": 2000.0,
            "team_possession_pct": 50.0, "primary_role": "CM", "metric_key": metric,
            "percentile": percentile, "value": percentile / 10, "reliability": 0.9}


def test_result_lists_shortlisted_candidates_by_tier():
    criteria = parse_criteria(["tackles:50", "interceptions:50"], PositionGroup.CENTRAL_MIDFIELD)
    rows = [row("a", "tackles", 90), row("a", "interceptions", 60),
            row("b", "tackles", 70), row("b", "interceptions", 55),
            row("c", "tackles", 95), row("c", "interceptions", 20)]
    result = build_scouting_result(rows, criteria, limit=10)
    assert (result["population_size"], result["shortlisted"], result["tier_1"]) == (3, 2, 1)
    assert [r["player_id"] for r in result["results"]] == ["a", "b"]
    assert result["results"][0]["criteria"][0] == {"key": "tackles", "percentile": 90, "value": 9.0,
                                                    "reliability_band": "high", "passes": True}


def test_near_misses_name_the_missed_criterion():
    criteria = parse_criteria(["tackles:50", "interceptions:50"], PositionGroup.CENTRAL_MIDFIELD)
    rows = [row("a", "tackles", 90), row("a", "interceptions", 47)]
    result = build_scouting_result(rows, criteria, limit=10)
    assert result["shortlisted"] == 0
    assert [(m["player_id"], m["missed"], m["gap"]) for m in result["near_misses"]] == [("a", "interceptions", 3.0)]


def test_presets_are_exposed_with_labels():
    presets = {p["key"]: p for p in presets_payload()}
    assert presets["ball_winning_midfielder"]["criteria"][0]["label"] == "Tackles"
