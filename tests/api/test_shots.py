from football_platform.api.shots import player_shot_map, team_shot_map


def shot(i, x, y, outcome="saved", xg=0.1, set_piece=None, period=1):
    return {"id": f"s{i}", "period": period, "start_x": x, "start_y": y, "set_piece": set_piece,
            "shot_outcome": outcome, "xg": xg}


def test_player_map_returns_zone_aggregates_only():
    rows = [shot(1, 102, 34, "goal", 0.5), shot(2, 70, 34, xg=0.02), shot(3, 94, 34, "goal", 0.78, "penalty")]
    baseline = rows + [shot(4, 95, 34, xg=0.15), shot(5, 95, 34, xg=0.15)]
    result = player_shot_map(rows, baseline, "ranked strikers")
    zones = {z["key"]: z for z in result["zones"]}
    assert zones["six_yard"]["shots"] == 1 and zones["six_yard"]["share"] == 0.5
    assert zones["box_central"]["baseline_share"] == 0.5  # 2 of 4 baseline non-penalty shots
    assert zones["edge"]["npxg_per_shot"] is None
    assert result["penalties"] == {"taken": 1, "scored": 1}
    assert all("start_x" not in z for z in result["zones"])  # no event-level data leaves the API


def test_team_map_splits_for_and_against():
    result = team_shot_map([shot(1, 102, 34, "goal", 0.5)], [shot(2, 70, 34)], [shot(1, 102, 34), shot(2, 70, 34)])
    assert result["for"]["totals"]["goals"] == 1 and result["against"]["totals"]["shots"] == 1
