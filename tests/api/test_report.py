from football_platform.api.report import highlights


def metric(key, percentile, band="high"):
    return {"key": key, "label": key.title(), "percentile": percentile, "reliability_band": band}


def themes(*metrics):
    return [{"metrics": list(metrics)}]


def test_highest_and_lowest_three_by_percentile():
    result = highlights(themes(*(metric(f"m{i}", p) for i, p in enumerate([10, 90, 50, 70, 30, 95, 5]))))
    assert result["split"]
    assert [m["percentile"] for m in result["highest"]] == [95, 90, 70]
    assert [m["percentile"] for m in result["lowest"]] == [5, 10, 30]
    assert [m["percentile"] for m in result["ranked"]] == [95, 90, 70, 50, 30, 10, 5]


def test_fewer_than_six_candidates_are_ranked_once_not_split():
    # Goalkeepers: two trusted count metrics, both low. Calling them "highest percentiles" would mislead.
    result = highlights(themes(metric("claims", 8), metric("sweeper", 3)))
    assert not result["split"]
    assert result["highest"] == [] and result["lowest"] == []
    assert [m["key"] for m in result["ranked"]] == ["claims", "sweeper"]


def test_low_reliability_and_ratios_are_not_candidates():
    result = highlights(themes(metric("noisy", 99, "low"), metric("ratio", 1, None), metric("solid", 60)))
    assert [m["key"] for m in result["ranked"]] == ["solid"]
    assert result["low_reliability"] == ["Noisy"]


def test_unranked_metrics_are_ignored():
    result = highlights(themes(metric("unranked", None, "low"), metric("a", 40)))
    assert [m["key"] for m in result["ranked"]] == ["a"]
    assert result["low_reliability"] == []


def test_split_lists_never_share_a_metric_at_the_minimum_size():
    result = highlights(themes(*(metric(f"m{i}", p) for i, p in enumerate([60, 50, 40, 30, 20, 10]))))
    assert not {m["key"] for m in result["highest"]} & {m["key"] for m in result["lowest"]}


def test_metric_repeated_across_themes_counts_once():
    result = highlights([{"metrics": [metric("a", 80)]}, {"metrics": [metric("a", 80), metric("b", 10)]}])
    assert [m["key"] for m in result["ranked"]] == ["a", "b"]
