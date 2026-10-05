"""Screening and weight-free ordering of candidates (docs/FOOTBALL_ANALYTICS.md, Phase 7).

No composite score: candidates are filtered on percentile thresholds, then ordered
by Pareto tier (non-dominated sorting), then by their weakest criterion (maximin).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

MAX_CRITERIA = 6
# Default tolerance for "near misses": a UI convenience, set by the user (Phase 7 doc).
DEFAULT_NEAR_MISS_POINTS = 5.0


@dataclass(frozen=True, slots=True)
class Criterion:
    metric_key: str
    min_percentile: float

    def __post_init__(self) -> None:
        if not 0 <= self.min_percentile <= 100:
            raise ValueError(f"min_percentile must be within 0-100, got {self.min_percentile}")


@dataclass(frozen=True, slots=True)
class Candidate:
    key: str  # opaque identifier (e.g. "player_id:season_id")
    minutes: float
    percentiles: tuple[float | None, ...]  # one per criterion, None = not ranked


@dataclass(frozen=True, slots=True)
class RankedCandidate:
    key: str
    tier: int
    weakest_percentile: float


def passes(candidate: Candidate, criteria: list[Criterion]) -> bool:
    """A missing percentile fails the criterion: the requirement cannot be verified."""
    return all(p is not None and p >= c.min_percentile for p, c in zip(candidate.percentiles, criteria))


def near_miss_gap(candidate: Candidate, criteria: list[Criterion]) -> float | None:
    """Points missing on the single failed criterion, if the candidate fails exactly one.

    Returns None when the candidate passes everything, fails several criteria, or the
    failed criterion has no percentile (cannot be verified).
    """
    gaps = []
    for percentile, criterion in zip(candidate.percentiles, criteria):
        if percentile is None:
            return None
        if percentile < criterion.min_percentile:
            gaps.append(criterion.min_percentile - percentile)
    return gaps[0] if len(gaps) == 1 else None


def near_misses(candidates: list[Candidate], criteria: list[Criterion],
                tolerance: float = DEFAULT_NEAR_MISS_POINTS) -> list[tuple[Candidate, float]]:
    """Candidates failing exactly one criterion by at most `tolerance` points, smallest gap first."""
    found = []
    for candidate in candidates:
        gap = near_miss_gap(candidate, criteria)
        if gap is not None and gap <= tolerance:
            found.append((candidate, gap))
    return sorted(found, key=lambda item: (item[1], -item[0].minutes, item[0].key))


def pareto_tiers(values: np.ndarray) -> np.ndarray:
    """Non-dominated sorting. values: (n candidates, k criteria), higher is better.

    Returns the 1-based tier of each row. Row i dominates j when it is >= on every
    criterion and > on at least one.
    """
    n = len(values)
    if n == 0:
        return np.zeros(0, dtype=int)
    ge = (values[:, None, :] >= values[None, :, :]).all(axis=2)
    gt = (values[:, None, :] > values[None, :, :]).any(axis=2)
    dominates = ge & gt  # dominates[i, j]: i dominates j
    tiers = np.zeros(n, dtype=int)
    remaining = np.ones(n, dtype=bool)
    tier = 0
    while remaining.any():
        tier += 1
        dominated = (dominates[remaining][:, remaining]).any(axis=0)
        current = np.flatnonzero(remaining)[~dominated]
        tiers[current] = tier
        remaining[current] = False
    return tiers


def rank_candidates(candidates: list[Candidate], criteria: list[Criterion]) -> list[RankedCandidate]:
    if not 1 <= len(criteria) <= MAX_CRITERIA:
        raise ValueError(f"Use between 1 and {MAX_CRITERIA} criteria")
    shortlisted = [c for c in candidates if passes(c, criteria)]
    if not shortlisted:
        return []
    values = np.array([c.percentiles for c in shortlisted], dtype=float)
    tiers = pareto_tiers(values)
    weakest = values.min(axis=1)
    order = sorted(
        range(len(shortlisted)),
        key=lambda i: (tiers[i], -weakest[i], -shortlisted[i].minutes, shortlisted[i].key),
    )
    return [RankedCandidate(shortlisted[i].key, int(tiers[i]), float(weakest[i])) for i in order]
