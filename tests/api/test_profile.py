import pytest

from football_platform.api.profile import build_profile, percentile_note, reliability_band

PLAYER_SEASON = {
    "player_id": "p1", "player_name": "Test Player", "nationality": "Testland", "season_id": "s1",
    "season_label": "2015/2016", "competition": "Premier League", "teams": ["Home FC"], "minutes": 2000.0,
    "appearances": 25, "starts": 22, "primary_role": "CF", "primary_role_share": 0.9,
    "position_group": "striker", "eligible": True, "team_possession_pct": 52.0, "population_size": 174,
    "population_seasons": ["s1"],
}


@pytest.mark.parametrize(("weight", "band"), [(0.95, "high"), (0.8, "high"), (0.6, "medium"), (0.3, "low"), (None, None)])
def test_reliability_bands(weight, band):
    assert reliability_band(weight) == band


def test_percentile_notes_explain_why_a_value_is_not_ranked():
    assert percentile_note("npxg", {"value": None}, True) == "unavailable"
    assert percentile_note("npxg", {"value": 0.4}, False) == "below_minutes_threshold"
    assert percentile_note("aerial_win_pct", {"value": 0.6}, True) == "insufficient_attempts"
    assert percentile_note("npxg", {"value": 0.4, "percentile": 80.0}, True) is None


def test_profile_follows_the_position_template_and_marks_possession_sensitive_themes():
    metrics = {"npxg": {"value": 0.5, "total": 11.1, "percentile": 90.0, "regressed": 0.45, "reliability": 0.7}}
    profile = build_profile(PLAYER_SEASON, metrics, 900.0)
    themes = {t["key"]: t for t in profile["themes"]}
    assert list(themes) == ["shooting", "creation", "progression", "defending", "aerial"]
    npxg = themes["shooting"]["metrics"][0]
    assert (npxg["key"], npxg["unit"], npxg["reliability_band"]) == ("npxg", "per_90", "medium")
    assert themes["defending"]["possession_sensitive"] and not themes["shooting"]["possession_sensitive"]
    # A metric without a stored row is reported as unavailable, never as zero.
    missing = themes["shooting"]["metrics"][1]
    assert missing["value"] is None and missing["percentile_note"] == "unavailable"


def test_goalkeeper_profile_shows_goalkeeping_first():
    gk = {**PLAYER_SEASON, "position_group": "goalkeeper", "primary_role": "GK"}
    assert build_profile(gk, {}, 900.0)["themes"][0]["key"] == "goalkeeping"


def test_every_profile_carries_the_data_source_notice():
    assert "StatsBomb" in build_profile(PLAYER_SEASON, {}, 900.0)["data_source"]["notice"]
