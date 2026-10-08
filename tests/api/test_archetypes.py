from football_platform.api.archetypes import overview, player_view

ROWS = [
    {"position_group": "striker", "archetype_index": 0, "size": 88, "more_features": ["aerials_won", "pressures"],
     "less_features": ["xt_carry"], "prototypes": [{"player_id": "p1", "season_id": "s", "name": "Rondón"}]},
    {"position_group": "striker", "archetype_index": 2, "size": 33, "more_features": ["npxg", "np_goals"],
     "less_features": ["pressures"], "prototypes": [{"player_id": "p2", "season_id": "s", "name": "Vardy"}]},
]


def test_types_are_described_with_metric_labels_not_invented_names():
    view = overview(ROWS)["groups"]["striker"][1]
    assert view["more"] == ["Non-penalty xG", "Non-penalty goals"]
    assert view["prototypes"][0]["name"] == "Vardy"


def test_player_between_two_types_is_flagged():
    clear = player_view({"position_group": "striker", "archetype_index": 2, "distance": 1.0, "second_index": 0,
                         "second_distance": 1.5}, ROWS)
    borderline = player_view({"position_group": "striker", "archetype_index": 2, "distance": 1.0, "second_index": 0,
                              "second_distance": 1.1}, ROWS)
    assert clear["also_close_to"] is None
    assert borderline["also_close_to"]["index"] == 0
    assert player_view(None, ROWS) is None
