"""Validation of the scouting report highlights (docs/FOOTBALL_ANALYTICS.md, Phase 11.8).

Highlights are chosen on first-half-season data with the report rule (api/report.py). We then read the same
metrics' percentiles in the second half: a "highest percentile" should stay high, a "lowest" should stay low.
We also test the reliability filter: among first-half percentiles >= 80, how many stay above the median,
for metrics of at least medium reliability vs low-reliability ones.

Run: cd scripts/validation && ../../.venv/bin/python phase11_report_validation.py
"""

from __future__ import annotations

import numpy as np

from football_platform.analytics.definitions import MetricKind, PositionGroup
from football_platform.analytics.profile_templates import TEMPLATES
from football_platform.api.profile import METRICS, reliability_band
from football_platform.api.report import highlights
from football_platform.database.connection import connect
from football_platform.reports.player_season_report import load_inputs

from phase6_validation import MIN_MINUTES_EACH_HALF, halves

HIGH_FIRST_HALF = 80.0


def column(key: str) -> str:
    return f"{key}_p90" if METRICS[key].kind is MetricKind.COUNT else key


def views(row, keys: list[str]) -> list[dict]:
    out = []
    for key in keys:
        pct = row.get(f"{column(key)}_pct_1")
        weight = row.get(f"{key}_reliability_1")
        out.append({"key": key, "label": key, "percentile": None if np.isnan(pct) else pct,
                    "reliability_band": None if weight is None or np.isnan(weight) else reliability_band(weight)})
    return out


def main() -> None:
    with connect() as conn:
        inputs = load_inputs(conn)
    h1, h2 = halves(inputs)
    both = h1.merge(h2, on=["player_id", "season_id"], suffixes=("_1", "_2"))
    both = both[(both["minutes_1"] >= MIN_MINUTES_EACH_HALF) & (both["minutes_2"] >= MIN_MINUTES_EACH_HALF)
                & (both["position_group_1"] == both["position_group_2"])]
    print(f"Players with >= {MIN_MINUTES_EACH_HALF:.0f} min in each half: {len(both)}")

    later_high, later_low, split_n, ranked_n = [], [], 0, 0
    stays = {"trusted": [], "low": []}
    for _, row in both.iterrows():
        group = row["position_group_1"]
        if not isinstance(group, str):
            continue
        keys = list(dict.fromkeys(k for ks in TEMPLATES[PositionGroup(group)].values() for k in ks))
        metric_views = views(row, keys)
        result = highlights([{"metrics": metric_views}])
        if not result["ranked"]:
            continue
        later = lambda key: row.get(f"{column(key)}_pct_2")  # noqa: E731
        if result["split"]:
            split_n += 1
            later_high += [later(m["key"]) for m in result["highest"]]
            later_low += [later(m["key"]) for m in result["lowest"]]
        else:
            ranked_n += 1
        for m in metric_views:
            if m["percentile"] is not None and m["percentile"] >= HIGH_FIRST_HALF and m["reliability_band"]:
                bucket = "low" if m["reliability_band"] == "low" else "trusted"
                stays[bucket].append(later(m["key"]) >= 50)

    high, low = np.array(later_high, float), np.array(later_low, float)
    high, low = high[~np.isnan(high)], low[~np.isnan(low)]
    print(f"Split into highest/lowest: {split_n} players; single ranked list: {ranked_n}")
    print(f"Second-half percentile of first-half 'highest': median {np.median(high):.0f}, "
          f">= 50 for {np.mean(high >= 50):.0%} (n={len(high)})")
    print(f"Second-half percentile of first-half 'lowest':  median {np.median(low):.0f}, "
          f"< 50 for {np.mean(low < 50):.0%} (n={len(low)})")
    for bucket, values in stays.items():
        print(f"First-half percentile >= {HIGH_FIRST_HALF:.0f}, reliability {bucket:>7}: "
              f"still >= 50 in second half {np.mean(values):.0%} (n={len(values)})")


if __name__ == "__main__":
    main()
