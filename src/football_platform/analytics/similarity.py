"""Player similarity (docs/FOOTBALL_ANALYTICS.md, "Phase 9a — Player similarity").

Profiles are vectors of per-90 metrics, z-scored within the position group.
Four distances are implemented; the one used by the application is chosen by the
fingerprint validation (scripts/validation/phase9_similarity_validation.py, decision D022).
"""

from __future__ import annotations

from enum import StrEnum

import numpy as np

from football_platform.analytics.definitions import ALL_METRICS, MetricKind, PositionGroup
from football_platform.analytics.profile_templates import TEMPLATES

METRICS = {m.key: m for m in ALL_METRICS}


class Distance(StrEnum):
    EUCLIDEAN = "euclidean"
    MAHALANOBIS = "mahalanobis"
    COSINE = "cosine"


def similarity_features(group: PositionGroup) -> list[str]:
    """Count metrics of the group's template that have a regressed estimate (Phase 4.1 §4)."""
    keys = [k for keys in TEMPLATES[group].values() for k in keys]
    return [k for k in keys if METRICS[k].kind is MetricKind.COUNT and METRICS[k].regress]


def zscore(matrix: np.ndarray, population: np.ndarray) -> np.ndarray:
    """Standardise columns with the population's mean and SD (constant columns map to 0)."""
    mean = population.mean(axis=0)
    sd = population.std(axis=0, ddof=1)
    sd = np.where(sd > 0, sd, 1.0)
    return (matrix - mean) / sd


def distances(target: np.ndarray, candidates: np.ndarray, method: Distance,
              population: np.ndarray | None = None) -> np.ndarray:
    """Distance from one z-scored profile to each row of `candidates` (z-scored the same way).

    Mahalanobis uses the covariance of `population` (z-scored), with a pseudo-inverse for stability.
    """
    diff = candidates - target
    if method is Distance.EUCLIDEAN:
        return np.sqrt((diff**2).sum(axis=1))
    if method is Distance.MAHALANOBIS:
        if population is None:
            raise ValueError("Mahalanobis distance needs the population covariance")
        inverse = np.linalg.pinv(np.cov(population, rowvar=False))
        return np.sqrt(np.einsum("ij,jk,ik->i", diff, inverse, diff).clip(min=0))
    if method is Distance.COSINE:
        norms = np.linalg.norm(candidates, axis=1) * np.linalg.norm(target)
        cosine = (candidates @ target) / np.where(norms > 0, norms, 1.0)
        return 1.0 - cosine
    raise ValueError(f"Unknown distance {method}")


def similarity_percentiles(candidate_distances: np.ndarray, population_distances: np.ndarray) -> np.ndarray:
    """Share (0-100) of the population that is farther from the target than each candidate."""
    sorted_population = np.sort(population_distances)
    farther = len(sorted_population) - np.searchsorted(sorted_population, candidate_distances, side="right")
    return farther / len(sorted_population) * 100
