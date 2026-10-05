"""Is a difference between two players real or within noise? (docs/FOOTBALL_ANALYTICS.md, Phase 6).

Uses the regressed estimates and their posterior standard deviations (Phase 4.1 §4).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

Z_95 = 1.96  # two-sided 95 % threshold for a difference of two independent estimates


class DifferenceVerdict(StrEnum):
    CLEAR = "clear"
    WITHIN_NOISE = "within_noise"
    NOT_TESTABLE = "not_testable"  # missing estimate or SD (e.g. ratios, unavailable metric)


@dataclass(frozen=True, slots=True)
class Estimate:
    regressed: float | None
    sd: float | None


def difference_verdict(a: Estimate, b: Estimate, z: float = Z_95) -> DifferenceVerdict:
    if a.regressed is None or b.regressed is None or a.sd is None or b.sd is None:
        return DifferenceVerdict.NOT_TESTABLE
    combined_sd = math.hypot(a.sd, b.sd)
    if combined_sd == 0:
        # Both values exact (no noise in the population): any difference is real.
        return DifferenceVerdict.CLEAR if a.regressed != b.regressed else DifferenceVerdict.WITHIN_NOISE
    return DifferenceVerdict.CLEAR if abs(a.regressed - b.regressed) > z * combined_sd else DifferenceVerdict.WITHIN_NOISE


@dataclass(frozen=True, slots=True)
class LeaderVerdict:
    leader_index: int | None
    verdict: DifferenceVerdict


def leader_verdict(estimates: list[Estimate]) -> LeaderVerdict:
    """Is the player with the highest regressed estimate clearly ahead of the second?"""
    testable = [(i, e) for i, e in enumerate(estimates) if e.regressed is not None and e.sd is not None]
    if len(testable) < 2:
        return LeaderVerdict(None, DifferenceVerdict.NOT_TESTABLE)
    ranked = sorted(testable, key=lambda item: item[1].regressed, reverse=True)
    (leader, first), (_, second) = ranked[0], ranked[1]
    return LeaderVerdict(leader, difference_verdict(first, second))
