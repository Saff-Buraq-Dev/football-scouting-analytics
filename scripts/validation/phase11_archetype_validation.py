"""Archetype validation (docs/FOOTBALL_ANALYTICS.md, Phase 11.7).

For each position group and k = 2..5: cluster first-half and second-half profiles independently and
measure agreement (adjusted Rand index) for the same players, on raw z-scores and on profile shapes
(z-scores centred per player, i.e. volume removed). A permutation null gives the chance level.

Run: cd scripts/validation && ../../.venv/bin/python phase11_archetype_validation.py
"""

from __future__ import annotations

import numpy as np

from football_platform.analytics.archetypes import kmeans, permutation_null, split_half_stability
from football_platform.analytics.definitions import PositionGroup
from football_platform.analytics.similarity import similarity_features, zscore
from football_platform.database.connection import connect
from football_platform.reports.player_season_report import load_inputs

from phase6_validation import MIN_MINUTES_EACH_HALF, halves

KS = range(2, 6)


def main() -> None:
    with connect() as conn:
        inputs = load_inputs(conn)
    first, second = halves(inputs)
    for group in PositionGroup:
        features = similarity_features(group)
        if len(features) < 3:
            print(f"{group.value}: skipped ({len(features)} features)")
            continue
        a = first[(first["position_group"] == group.value) & (first["minutes"] >= MIN_MINUTES_EACH_HALF)]
        b = second[(second["position_group"] == group.value) & (second["minutes"] >= MIN_MINUTES_EACH_HALF)]
        both = a.merge(b, on=["player_id", "season_id"], suffixes=("_1", "_2"))
        x1 = both[[f"{f}_p90_regressed_1" for f in features]].to_numpy(float)
        x2 = both[[f"{f}_p90_regressed_2" for f in features]].to_numpy(float)
        raw1, raw2 = zscore(x1, x1), zscore(x2, x2)
        shape1, shape2 = raw1 - raw1.mean(axis=1, keepdims=True), raw2 - raw2.mean(axis=1, keepdims=True)
        volume_gap = np.ptp(kmeans(raw1, 2).centroids.mean(axis=1))
        print(f"\n{group.value} (n = {len(both)}): raw k=2 split = volume gap {volume_gap:.2f} SD in mean z")
        for label, s1, s2 in (("raw  ", raw1, raw2), ("shape", shape1, shape2)):
            cells = []
            for k in KS:
                ari = split_half_stability(s1, s2, k)
                null = np.percentile(permutation_null(s1, s2, k), 99)
                cells.append(f"k={k} {ari:.2f} (null99 {null:.2f})")
            print(f"   {label}: " + " | ".join(cells))


if __name__ == "__main__":
    main()
