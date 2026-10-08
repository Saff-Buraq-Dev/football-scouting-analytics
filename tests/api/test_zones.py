from football_platform.api.zones import build_zone_maps, frame, map_counts


def event(**kw):
    base = {"period": 1, "type": "pass", "outcome": "success", "set_piece": None,
            "start_x": 40.0, "start_y": 34.0, "end_x": 70.0, "end_y": 60.0}
    return {**base, **kw}


def test_zone_maps_return_aggregates_with_group_baseline():
    own = [event(), event(type="shot", outcome="fail", start_x=95.0)]
    received = [event(end_x=100.0, end_y=34.0)]
    group = map_counts(frame(own * 2 + [event(start_x=5.0)]), frame(received))
    result = build_zone_maps(own, received, group, "striker")
    maps = {m["key"]: m for m in result["maps"]}
    assert maps["touches"]["total"] == 2 and maps["receptions"]["total"] == 1
    assert sum(z["share"] for z in maps["touches"]["zones"]) == 1.0
    left_wing_strip_4 = next(z for z in maps["progression"]["zones"] if z["strip"] == 4 and z["channel"] == "left_wing")
    assert left_wing_strip_4["count"] == 1  # ends at y = 60: beyond the box line (54.16), on the attacker's left wing
    assert all("start_x" not in z for m in result["maps"] for z in m["zones"])  # aggregates only
