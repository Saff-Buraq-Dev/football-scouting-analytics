import numpy as np
import pytest

from football_platform.analytics.definitions import PositionGroup
from football_platform.analytics.similarity import (
    Distance,
    distances,
    similarity_features,
    similarity_percentiles,
    zscore,
)


def test_features_are_the_regressed_count_metrics_of_the_template():
    features = similarity_features(PositionGroup.CENTRAL_MIDFIELD)
    assert "progressive_passes" in features and "tackles" in features
    assert "pass_completion" not in features  # ratio: excluded in v1


def test_zscore_uses_the_population_and_handles_constant_columns():
    population = np.array([[1.0, 5.0], [3.0, 5.0]])
    z = zscore(np.array([[2.0, 5.0], [3.0, 5.0]]), population)
    assert z[:, 0] == pytest.approx([0.0, 1 / np.sqrt(2)])
    assert (z[:, 1] == 0).all()


def test_euclidean_and_cosine_distances():
    target = np.array([1.0, 0.0])
    candidates = np.array([[1.0, 0.0], [2.0, 0.0], [0.0, 1.0]])
    assert distances(target, candidates, Distance.EUCLIDEAN) == pytest.approx([0.0, 1.0, np.sqrt(2)])
    # Cosine ignores volume: [2, 0] has the same shape as [1, 0].
    assert distances(target, candidates, Distance.COSINE) == pytest.approx([0.0, 0.0, 1.0])


def test_mahalanobis_discounts_correlated_metrics():
    rng = np.random.default_rng(0)
    x = rng.normal(size=500)
    population = np.column_stack([x, x + rng.normal(scale=0.1, size=500)])  # two near-duplicate metrics
    target = np.array([0.0, 0.0])
    along = np.array([[1.0, 1.0]])   # moves along the shared direction (common in the population)
    across = np.array([[1.0, -1.0]])  # moves against it (rare)
    d_along = distances(target, along, Distance.MAHALANOBIS, population)[0]
    d_across = distances(target, across, Distance.MAHALANOBIS, population)[0]
    assert d_across > 5 * d_along
    with pytest.raises(ValueError):
        distances(target, along, Distance.MAHALANOBIS)


def test_similarity_percentile_is_the_share_of_the_population_farther_away():
    population = np.array([1.0, 2.0, 3.0, 4.0])
    assert similarity_percentiles(np.array([1.0, 2.5, 4.0]), population) == pytest.approx([75.0, 50.0, 0.0])
