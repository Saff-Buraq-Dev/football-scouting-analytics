"""Fingerprint test for player similarity (docs/FOOTBALL_ANALYTICS.md, Phase 9a).

For each position group: first-half and second-half profiles of the same players.
For every second-half profile, rank all first-half profiles by distance and record
the rank of the same player. A good method recognises the player himself.

Run: cd scripts/validation && ../../.venv/bin/python phase9_similarity_validation.py
"""

from __future__ import annotations

import numpy as np

from football_platform.analytics.definitions import PositionGroup
from football_platform.analytics.similarity import Distance, distances, similarity_features, zscore
from football_platform.database.connection import connect
from football_platform.reports.player_season_report import load_inputs

from phase6_validation import MIN_MINUTES_EACH_HALF, halves

METHODS = {
    "Euclidean, observed per 90": ("p90", Distance.EUCLIDEAN),
    "Euclidean, regressed per 90": ("p90_regressed", Distance.EUCLIDEAN),
    "Mahalanobis, regressed": ("p90_regressed", Distance.MAHALANOBIS),
    "Cosine, regressed": ("p90_regressed", Distance.COSINE),
}


def main() -> None:
    with connect() as conn:
        inputs = load_inputs(conn)
    first, second = halves(inputs)
    results = {name: {"ranks": [], "sizes": []} for name in METHODS}

    for group in PositionGroup:
        features = similarity_features(group)
        if len(features) < 3:
            continue  # too few dimensions for a meaningful profile (e.g. goalkeepers)
        keys = ["player_id", "season_id"]
        h1 = first[(first["position_group"] == group.value) & (first["minutes"] >= MIN_MINUTES_EACH_HALF)]
        h2 = second[(second["position_group"] == group.value) & (second["minutes"] >= MIN_MINUTES_EACH_HALF)]
        both = h1.merge(h2, on=keys, suffixes=("_1", "_2"))
        if len(both) < 20:
            continue
        for name, (suffix, method) in METHODS.items():
            a = both[[f"{f}_{suffix}_1" for f in features]].to_numpy(dtype=float)
            b = both[[f"{f}_{suffix}_2" for f in features]].to_numpy(dtype=float)
            za, zb = zscore(a, a), zscore(b, b)
            for i in range(len(both)):
                d = distances(zb[i], za, method, population=za)
                rank = int((d < d[i]).sum()) + 1  # 1 = the same player is the closest profile
                results[name]["ranks"].append(rank)
                results[name]["sizes"].append(len(both))
        print(f"{group.value:<28} {len(both):>4} players, {len(features)} features")

    sizes = np.array(results[next(iter(METHODS))]["sizes"])
    print(f"\nRandom baseline: top-1 {np.mean(1 / sizes):.1%}, top-5 {np.mean(np.minimum(5 / sizes, 1)):.1%}, "
          f"median rank ~{np.median(sizes) / 2:.0f}")
    print(f"{'method':<30}{'top-1':>8}{'top-5':>8}{'top-10%':>9}{'median rank':>13}")
    for name, data in results.items():
        ranks, n = np.array(data["ranks"]), np.array(data["sizes"])
        print(f"{name:<30}{(ranks == 1).mean():>8.1%}{(ranks <= 5).mean():>8.1%}"
              f"{(ranks <= np.ceil(0.1 * n)).mean():>9.1%}{np.median(ranks):>13.0f}")


if __name__ == "__main__":
    main()
