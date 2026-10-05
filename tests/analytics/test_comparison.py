import pytest

from football_platform.analytics.comparison import (
    DifferenceVerdict as V,
    Estimate,
    difference_verdict,
    leader_verdict,
)


def test_difference_larger_than_two_combined_sds_is_clear():
    # combined sd = 0.05; threshold = 0.098
    assert difference_verdict(Estimate(0.50, 0.03), Estimate(0.40, 0.04)) is V.CLEAR
    assert difference_verdict(Estimate(0.45, 0.03), Estimate(0.40, 0.04)) is V.WITHIN_NOISE


def test_more_uncertainty_turns_the_same_gap_into_noise():
    gap = (0.50, 0.40)
    assert difference_verdict(Estimate(gap[0], 0.02), Estimate(gap[1], 0.02)) is V.CLEAR
    assert difference_verdict(Estimate(gap[0], 0.06), Estimate(gap[1], 0.06)) is V.WITHIN_NOISE


def test_missing_estimates_are_not_testable():
    assert difference_verdict(Estimate(None, None), Estimate(0.4, 0.05)) is V.NOT_TESTABLE


def test_leader_is_tested_against_the_second_only():
    estimates = [Estimate(0.30, 0.02), Estimate(0.62, 0.03), Estimate(0.55, 0.03), Estimate(0.10, 0.02)]
    verdict = leader_verdict(estimates)
    assert verdict.leader_index == 1
    assert verdict.verdict is V.WITHIN_NOISE  # 0.62 vs 0.55: gap 0.07 < 1.96 * 0.042


@pytest.mark.parametrize("estimates", [[], [Estimate(0.5, 0.1)], [Estimate(None, None), Estimate(0.3, 0.1)]])
def test_leader_needs_two_testable_players(estimates):
    assert leader_verdict(estimates).verdict is V.NOT_TESTABLE
