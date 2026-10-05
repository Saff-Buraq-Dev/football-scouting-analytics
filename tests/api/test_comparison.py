import pytest

from football_platform.api.comparison import build_comparison, comparison_metrics

BASE = {"player_name": "P", "teams": ["T"], "competition": "Premier League", "season_label": "2015/2016",
        "primary_role": "CF", "minutes": 2500.0, "eligible": True, "team_possession_pct": 50.0,
        "population_group_size": 174, "season_id": "s1"}


def player(pid, group="striker", **kw):
    return {**BASE, "player_id": pid, "position_group": group, **kw}


def metric(regressed, sd, value=None):
    return {"value": value if value is not None else regressed, "total": None, "percentile": 50.0,
            "regressed": regressed, "reliability": 0.8, "regressed_sd": sd}


def test_same_group_uses_its_template_only():
    themes = dict(comparison_metrics(["striker", "striker"]))
    assert themes[next(iter(themes))][0] == "npxg"
    assert all("gk_np_save_pct" not in keys for keys in themes.values())


def test_mixed_groups_take_the_union_with_the_first_players_template_first():
    themes = comparison_metrics(["centre_back", "striker"])
    assert themes[0][0].value == "progression"  # centre-back template comes first
    keys = [k for _, ks in themes for k in ks]
    assert "npxg" in keys and "interceptions" in keys and len(keys) == len(set(keys))


def test_two_players_get_a_pair_verdict_and_mixed_groups_a_warning():
    result = build_comparison(
        [player("a"), player("b", group="attacking_midfield_winger")],
        [{"npxg": metric(0.50, 0.03)}, {"npxg": metric(0.30, 0.03)}],
    )
    npxg = next(m for t in result["themes"] for m in t["metrics"] if m["key"] == "npxg")
    assert npxg["pair_verdict"] == "clear"
    assert npxg["leader"] == {"index": 0, "verdict": "clear"}
    assert "mixed_position_groups" in result["warnings"]


def test_three_players_report_whether_the_leader_is_clearly_ahead():
    result = build_comparison(
        [player("a"), player("b"), player("c")],
        [{"npxg": metric(0.40, 0.04)}, {"npxg": metric(0.45, 0.04)}, {"npxg": metric(0.20, 0.04)}],
    )
    npxg = next(m for t in result["themes"] for m in t["metrics"] if m["key"] == "npxg")
    assert npxg["leader"] == {"index": 1, "verdict": "within_noise"}
    assert "pair_verdict" not in npxg


@pytest.mark.parametrize("count", [1, 5])
def test_player_count_is_bounded(count):
    with pytest.raises(ValueError):
        build_comparison([player(str(i)) for i in range(count)], [{}] * count)
