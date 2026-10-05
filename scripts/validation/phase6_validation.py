"""Validation of the "clear difference" rule (docs/FOOTBALL_ANALYTICS.md, Phase 6).

For every pair of players in the same position group, the difference on each metric
is judged with first-half-season data only (regressed estimates + posterior SD).
We then measure how often the sign of that difference holds in the second half.

Run: .venv/bin/python scripts/validation/phase6_validation.py   (needs the loaded database)
"""

from __future__ import annotations

import numpy as np

from football_platform.analytics.comparison import Z_95
from football_platform.database.connection import connect
from football_platform.reports.player_season_report import compute, load_inputs

MIN_MINUTES_EACH_HALF = 450.0
METRICS = ["npxg", "xa", "key_passes", "progressive_passes", "tackles", "interceptions", "np_goals", "assists"]


def halves(inputs):
    matches = inputs.matches.copy()
    matches["rank"] = matches.groupby("season_id")["match_date"].rank(method="first")
    last = matches.groupby("season_id")["rank"].transform("max")
    first = set(matches.loc[matches["rank"] <= last / 2, "id"])
    second = set(matches["id"]) - first
    return compute(inputs, MIN_MINUTES_EACH_HALF, first), compute(inputs, MIN_MINUTES_EACH_HALF, second)


def main() -> None:
    with connect() as conn:
        inputs = load_inputs(conn)
    h1, h2 = halves(inputs)
    both = h1.merge(h2, on=["player_id", "season_id"], suffixes=("_1", "_2"))
    both = both[(both["minutes_1"] >= MIN_MINUTES_EACH_HALF) & (both["minutes_2"] >= MIN_MINUTES_EACH_HALF)
                & (both["position_group_1"] == both["position_group_2"])]

    print(f"Players with >= {MIN_MINUTES_EACH_HALF:.0f} min in each half: {len(both)}")
    print(f"{'metric':<20}{'pairs':>9}{'clear':>8}{'persist|clear':>15}{'persist|noise':>15}")
    for metric in METRICS:
        clear_hits = clear_n = noise_hits = noise_n = 0
        for _, group in both.groupby("position_group_1"):
            r = group[f"{metric}_p90_regressed_1"].to_numpy()
            sd = group[f"{metric}_p90_regressed_sd_1"].to_numpy()
            later = group[f"{metric}_p90_2"].to_numpy()
            i, j = np.triu_indices(len(group), k=1)
            diff = r[i] - r[j]
            later_diff = later[i] - later[j]
            valid = ~np.isnan(diff) & ~np.isnan(later_diff) & (diff != 0) & (later_diff != 0)
            clear = np.abs(diff) > Z_95 * np.hypot(sd[i], sd[j])
            persists = np.sign(diff) == np.sign(later_diff)
            clear_n += int((valid & clear).sum())
            clear_hits += int((valid & clear & persists).sum())
            noise_n += int((valid & ~clear).sum())
            noise_hits += int((valid & ~clear & persists).sum())
        total = clear_n + noise_n
        print(f"{metric:<20}{total:>9}{clear_n / total:>8.0%}{clear_hits / clear_n:>15.0%}{noise_hits / noise_n:>15.0%}")


if __name__ == "__main__":
    main()
