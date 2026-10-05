"""Assemble a "similar players" result (pure logic). Method: FOOTBALL_ANALYTICS.md, Phase 9a; D022."""

from __future__ import annotations

from typing import Any

import numpy as np

from football_platform.analytics.definitions import ALL_METRICS
from football_platform.analytics.similarity import Distance, distances, similarity_percentiles, zscore
from football_platform.api.profile import DATA_SOURCE

LABELS = {m.key: m.label for m in ALL_METRICS}
METHOD = Distance.EUCLIDEAN  # selected by the fingerprint validation (D022)
DIFFERENCES_SHOWN = 2
NOTE = (
    "Similarity compares regressed per-90 profiles of the role's key actions (z-scores within the position "
    "group, Euclidean distance). In a half-season test a player's own profile was found among his 10 % nearest "
    "neighbours about 60 % of the time: read the list as a neighbourhood of comparable profiles, not exact matches."
)


class SimilarityUnavailableError(ValueError):
    pass


def build_similarity(rows: list[dict[str, Any]], features: list[str], target_key: str, limit: int) -> dict[str, Any]:
    players: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = f"{row['player_id']}:{row['season_id']}"
        player = players.setdefault(key, {k: row[k] for k in (
            "player_id", "season_id", "player_name", "teams", "competition", "minutes", "eligible",
            "team_possession_pct")} | {"values": {}})
        player["values"][row["metric_key"]] = row["regressed"]

    complete = {k: p for k, p in players.items() if all(p["values"].get(f) is not None for f in features)}
    if target_key not in complete:
        raise SimilarityUnavailableError("The player has no regressed profile for this role")
    population_keys = [k for k, p in complete.items() if p["eligible"] and k != target_key]
    if len(population_keys) < 2:
        raise SimilarityUnavailableError("Not enough players in the reference population")

    matrix = np.array([[complete[k]["values"][f] for f in features] for k in population_keys])
    target = np.array([complete[target_key]["values"][f] for f in features])
    z_population = zscore(matrix, matrix)
    z_target = zscore(target[None, :], matrix)[0]
    d = distances(z_target, z_population, METHOD)
    order = np.argsort(d, kind="stable")[:limit]
    percentiles = similarity_percentiles(d[order], d)

    def explain(i: int) -> list[dict[str, Any]]:
        diff = z_population[i] - z_target
        top = np.argsort(-np.abs(diff))[:DIFFERENCES_SHOWN]
        return [{"key": features[j], "label": LABELS[features[j]], "direction": "more" if diff[j] > 0 else "fewer",
                 "z_difference": float(diff[j])} for j in top]

    target_player = complete[target_key]
    return {
        "target": {k: v for k, v in target_player.items() if k != "values"},
        "features": [{"key": f, "label": LABELS[f], "target_z": float(z_target[j])} for j, f in enumerate(features)],
        "population_size": len(population_keys),
        "results": [
            {
                **{k: v for k, v in complete[population_keys[i]].items() if k != "values"},
                "rank": rank,
                "distance": float(d[i]),
                "similarity_percentile": float(pct),
                "profile_z": [float(z) for z in z_population[i]],
                "main_differences": explain(i),
            }
            for rank, (i, pct) in enumerate(zip(order, percentiles), start=1)
        ],
        "method_note": NOTE,
        "data_source": DATA_SOURCE,
    }
