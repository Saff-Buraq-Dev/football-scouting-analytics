import numpy as np
import pytest

from football_platform.analytics.archetypes import (
    ALSO_CLOSE_RATIO,
    adjusted_rand_index,
    fit_archetypes,
    kmeans,
    profile_shapes,
)


def blobs(seed=0):
    rng = np.random.default_rng(seed)
    a = rng.normal([0, 0], 0.2, size=(40, 2))
    b = rng.normal([5, 5], 0.2, size=(40, 2))
    return np.vstack([a, b]), np.array([0] * 40 + [1] * 40)


def test_kmeans_recovers_separated_groups_deterministically():
    x, truth = blobs()
    first, second = kmeans(x, 2), kmeans(x, 2)
    assert adjusted_rand_index(first.labels, truth) == pytest.approx(1.0)
    assert np.array_equal(first.labels, second.labels)  # fixed seed: reproducible


def test_adjusted_rand_index_reference_values():
    labels = np.array([0, 0, 1, 1, 2, 2])
    assert adjusted_rand_index(labels, labels) == pytest.approx(1.0)
    assert adjusted_rand_index(labels, np.array([5, 5, 7, 7, 9, 9])) == pytest.approx(1.0)  # names don't matter
    rng = np.random.default_rng(1)
    random = [adjusted_rand_index(rng.integers(0, 3, 300), rng.integers(0, 3, 300)) for _ in range(50)]
    assert abs(np.mean(random)) < 0.02  # chance level ≈ 0


def test_profile_shape_removes_volume():
    values = np.array([[1.0, 2.0, 3.0], [2.0, 4.0, 6.0]])
    shapes = profile_shapes(values, np.zeros(3), np.ones(3))
    assert shapes.mean(axis=1) == pytest.approx([0.0, 0.0])
    assert np.allclose(shapes[0] * 2, shapes[1])  # same shape, different volume


def test_archetype_model_describes_types_and_assigns_players():
    rng = np.random.default_rng(3)
    winners = rng.normal([3.0, 0.5, 2.5], 0.2, size=(60, 3))   # many tackles and pressures, few key passes
    creators = rng.normal([1.0, 2.5, 0.8], 0.2, size=(40, 3))  # many key passes
    model = fit_archetypes("central_midfield", ["tackles", "key_passes", "pressures"], np.vstack([winners, creators]))
    assert model.describe(0)["less"][0] == "key_passes"      # largest type first: the ball-winners
    assert model.describe(1)["more"][0] == "key_passes"
    order, distances = model.assign(np.array([[1.0, 2.5, 0.8]]))
    assert order[0, 0] == 1 and distances[0, 1] / distances[0, 0] > ALSO_CLOSE_RATIO
