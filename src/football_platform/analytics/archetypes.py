"""Player archetypes: k-means within position groups, k chosen by half-season stability.

Method: docs/FOOTBALL_ANALYTICS.md, "Phase 11.7". Pure NumPy, deterministic (fixed seed).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

SEED = 2015
RESTARTS = 20
MAX_ITERATIONS = 300


@dataclass(frozen=True)
class KMeansResult:
    centroids: np.ndarray
    labels: np.ndarray
    inertia: float


def _plus_plus_init(x: np.ndarray, k: int, rng: np.random.Generator) -> np.ndarray:
    centroids = [x[rng.integers(len(x))]]
    for _ in range(1, k):
        d2 = np.min(((x[:, None, :] - np.array(centroids)[None]) ** 2).sum(axis=2), axis=1)
        centroids.append(x[rng.choice(len(x), p=d2 / d2.sum())])
    return np.array(centroids)


def kmeans(x: np.ndarray, k: int, seed: int = SEED, restarts: int = RESTARTS) -> KMeansResult:
    """Lloyd's algorithm with k-means++ initialisation; best of `restarts` runs (lowest inertia)."""
    rng = np.random.default_rng(seed)
    best: KMeansResult | None = None
    for _ in range(restarts):
        centroids = _plus_plus_init(x, k, rng)
        for _ in range(MAX_ITERATIONS):
            labels = assign(x, centroids)
            updated = np.array([x[labels == j].mean(axis=0) if (labels == j).any() else centroids[j] for j in range(k)])
            if np.allclose(updated, centroids):
                break
            centroids = updated
        labels = assign(x, centroids)
        inertia = float(((x - centroids[labels]) ** 2).sum())
        if best is None or inertia < best.inertia:
            best = KMeansResult(centroids, labels, inertia)
    assert best is not None
    return best


def assign(x: np.ndarray, centroids: np.ndarray) -> np.ndarray:
    return np.argmin(((x[:, None, :] - centroids[None]) ** 2).sum(axis=2), axis=1)


def adjusted_rand_index(a: np.ndarray, b: np.ndarray) -> float:
    """Agreement between two partitions of the same items, corrected for chance (1 = identical, ~0 = random)."""
    _, a_idx = np.unique(a, return_inverse=True)
    _, b_idx = np.unique(b, return_inverse=True)
    table = np.zeros((a_idx.max() + 1, b_idx.max() + 1))
    np.add.at(table, (a_idx, b_idx), 1)
    comb = lambda n: n * (n - 1) / 2  # noqa: E731
    index = comb(table).sum()
    rows, cols, total = comb(table.sum(axis=1)).sum(), comb(table.sum(axis=0)).sum(), comb(len(a))
    expected = rows * cols / total
    maximum = (rows + cols) / 2
    return float((index - expected) / (maximum - expected)) if maximum != expected else 1.0


def split_half_stability(first: np.ndarray, second: np.ndarray, k: int) -> float:
    """Cluster each half independently; ARI of the two partitions of the same players."""
    return adjusted_rand_index(kmeans(first, k).labels, kmeans(second, k).labels)


def permutation_null(first: np.ndarray, second: np.ndarray, k: int, permutations: int = 50,
                     seed: int = SEED) -> np.ndarray:
    """Stability when second-half profiles are shuffled across players (no shared structure)."""
    rng = np.random.default_rng(seed)
    first_labels = kmeans(first, k, restarts=5).labels
    second_labels = kmeans(second, k, restarts=5).labels
    return np.array([adjusted_rand_index(first_labels, rng.permutation(second_labels)) for _ in range(permutations)])


# -- Production model ------------------------------------------------------------------

# Number of types per position group: the k with the highest half-season stability on profile
# SHAPES (scripts/validation/phase11_archetype_validation.py, docs/FOOTBALL_ANALYTICS.md Phase 11.7).
# Goalkeepers are excluded: only two template count metrics.
ARCHETYPE_K = {
    "centre_back": 2,
    "full_back": 2,
    "central_midfield": 2,
    "attacking_midfield_winger": 2,
    "striker": 3,
}
DESCRIPTOR_FEATURES = 3  # distinctive statistics listed per type ("more ...")
PROTOTYPES = 5  # most typical players listed per type
# Display convention: a player whose second-nearest type is within 15 % of the nearest distance is
# shown as "also close to" that type (archetypes are tendencies: half-season stability ARI ≈ 0.2–0.35).
ALSO_CLOSE_RATIO = 1.15


def profile_shapes(values: np.ndarray, mean: np.ndarray, sd: np.ndarray) -> np.ndarray:
    """z-scores against the group, then centred per player: the profile's shape, not its volume."""
    z = (values - mean) / np.where(sd > 0, sd, 1.0)
    return z - z.mean(axis=1, keepdims=True)


@dataclass(frozen=True)
class ArchetypeModel:
    position_group: str
    features: list[str]
    mean: np.ndarray
    sd: np.ndarray
    centroids: np.ndarray

    def describe(self, index: int) -> dict[str, list[str]]:
        order = np.argsort(self.centroids[index])
        return {"more": [self.features[i] for i in order[::-1][:DESCRIPTOR_FEATURES]],
                "less": [self.features[i] for i in order[:2]]}

    def assign(self, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """(sorted type indices, sorted distances) per player, nearest first."""
        shapes = profile_shapes(values, self.mean, self.sd)
        d = np.sqrt(((shapes[:, None, :] - self.centroids[None]) ** 2).sum(axis=2))
        order = np.argsort(d, axis=1)
        return order, np.take_along_axis(d, order, axis=1)


def fit_archetypes(position_group: str, features: list[str], population_values: np.ndarray) -> ArchetypeModel:
    mean, sd = population_values.mean(axis=0), population_values.std(axis=0, ddof=1)
    shapes = profile_shapes(population_values, mean, sd)
    result = kmeans(shapes, ARCHETYPE_K[position_group])
    # Stable ordering of types (k-means labels are arbitrary): by size, largest first.
    sizes = np.bincount(result.labels, minlength=len(result.centroids))
    centroids = result.centroids[np.argsort(-sizes, kind="stable")]
    return ArchetypeModel(position_group, features, mean, sd, centroids)
