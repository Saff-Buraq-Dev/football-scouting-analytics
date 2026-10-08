from football_platform.api.pressing import build_pressing_maps, counts


def action(type_, x, y=34.0, outcome="success", duel_kind=None):
    return {"type": type_, "outcome": outcome, "duel_kind": duel_kind, "period": 1, "start_x": x, "start_y": y}


def test_pressing_maps_split_actions_and_ball_wins():
    team = [action("interception", 90.0), action("duel", 50.0, outcome="fail", duel_kind="ground"),
            action("foul_committed", 60.0, outcome="not_applicable"), action("ball_recovery", 20.0)]
    result = build_pressing_maps(team, counts(team + [action("interception", 10.0)]))
    maps = {m["key"]: m for m in result["maps"]}
    assert maps["defensive_actions"]["total"] == 4
    assert maps["ball_wins"]["total"] == 2  # interception + successful recovery; lost tackle and foul excluded
    top_strip = sum(z["count"] for z in maps["ball_wins"]["zones"] if z["strip"] == 5)
    assert top_strip == 1  # the interception at 90 m, in the final strip
