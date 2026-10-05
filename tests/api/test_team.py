from football_platform.api.team import build_team_profile, team_list_item

TEAM = {"team_id": "t1", "season_id": "s1", "team_name": "Leicester City", "competition": "Premier League",
        "season_label": "2015/2016", "matches": 38, "points": 81, "goals_for": 68, "goals_against": 36,
        "league_size": 20}
METRICS = {"points_per_match": {"value": 2.13, "percentile": 100.0},
           "xpts_per_match": {"value": 1.74, "percentile": 85.0},
           "ppda": {"value": 16.3, "percentile": 65.0}}


def test_profile_reports_points_versus_expected_and_explains_inverted_metrics():
    profile = build_team_profile(TEAM, METRICS, squad=[])
    assert round(profile["points_vs_expected_per_match"], 2) == 0.39
    ppda = next(r for r in profile["style"] if r["key"] == "ppda")
    assert ppda["note"].startswith("Lower = more intense pressing")
    missing = next(r for r in profile["style"] if r["key"] == "counter_npxg_share")
    assert missing["value"] is None  # unavailable, not zero


def test_list_item_flattens_metric_values():
    item = team_list_item(TEAM, METRICS)
    assert item["metrics"]["ppda"] == 16.3 and item["metrics"]["long_pass_share"] is None
