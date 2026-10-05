import numpy as np
import pytest

from football_platform.analytics.definitions import ALL_METRICS
from football_platform.analytics.scouting import Candidate, Criterion, pareto_tiers, passes, rank_candidates
from football_platform.analytics.scouting_presets import PRESETS

CRITERIA = [Criterion("tackles", 50), Criterion("interceptions", 50)]


def test_pareto_tiers_on_a_known_example():
    values = np.array([
        [90, 60],  # A: tier 1 (best tackles)
        [60, 90],  # B: tier 1 (best interceptions)
        [80, 80],  # C: tier 1 (not dominated: A and B each lose on one axis)
        [70, 70],  # D: dominated by C -> tier 2
        [55, 55],  # E: dominated by D -> tier 3
    ])
    assert pareto_tiers(values).tolist() == [1, 1, 1, 2, 3]


def test_identical_candidates_share_a_tier():
    assert pareto_tiers(np.array([[70, 70], [70, 70]])).tolist() == [1, 1]


def test_missing_percentile_fails_the_criterion():
    assert not passes(Candidate("x", 2000, (80.0, None)), CRITERIA)
    assert passes(Candidate("x", 2000, (80.0, 50.0)), CRITERIA)


def test_ranking_orders_by_tier_then_weakest_criterion_then_minutes():
    candidates = [
        Candidate("balanced", 2000, (80.0, 80.0)),
        Candidate("specialist", 3000, (99.0, 55.0)),
        Candidate("dominated", 3000, (70.0, 70.0)),
        Candidate("fails", 3000, (95.0, 40.0)),
        Candidate("twin_more_minutes", 2500, (80.0, 80.0)),
    ]
    ranked = rank_candidates(candidates, CRITERIA)
    assert [r.key for r in ranked] == ["twin_more_minutes", "balanced", "specialist", "dominated"]
    assert [r.tier for r in ranked] == [1, 1, 1, 2]
    assert ranked[2].weakest_percentile == 55.0


@pytest.mark.parametrize("criteria", [[], [Criterion("tackles", 50)] * 7])
def test_criteria_count_is_bounded(criteria):
    with pytest.raises(ValueError):
        rank_candidates([], criteria)


def test_presets_use_known_metrics_valid_for_their_group():
    metrics = {m.key: m for m in ALL_METRICS}
    for preset in PRESETS:
        for criterion in preset.criteria:
            spec = metrics[criterion.metric_key]
            assert spec.position_groups is None or preset.position_group.value in spec.position_groups
    assert len({p.key for p in PRESETS}) == len(PRESETS)


def test_near_misses_fail_exactly_one_criterion_within_tolerance():
    from football_platform.analytics.scouting import near_misses

    candidates = [
        Candidate("just_short", 2000, (47.0, 80.0)),   # misses tackles by 3 -> near miss
        Candidate("far_short", 2000, (30.0, 80.0)),    # misses by 20 -> no
        Candidate("two_misses", 2000, (48.0, 49.0)),   # misses two -> no
        Candidate("passes", 2000, (60.0, 60.0)),       # passes -> not a near miss
        Candidate("unverifiable", 2000, (49.0, None)), # missing percentile -> no
        Candidate("closest", 1500, (80.0, 49.0)),      # misses interceptions by 1 -> first
    ]
    result = near_misses(candidates, CRITERIA, tolerance=5)
    assert [(c.key, gap) for c, gap in result] == [("closest", 1.0), ("just_short", 3.0)]
