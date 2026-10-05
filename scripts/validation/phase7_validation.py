"""Shortlist stability (docs/FOOTBALL_ANALYTICS.md, Phase 7).

For each role preset, build the shortlist (and near misses) on first-half-season data,
then measure on second-half data:
- how many still meet every criterion ("pass");
- their mean percentile on the criteria (50 = an average player of the group).

Run: .venv/bin/python scripts/validation/phase7_validation.py   (needs the loaded database)
"""

from __future__ import annotations

from football_platform.analytics.definitions import ALL_METRICS, MetricKind
import numpy as np

from football_platform.analytics.scouting import Candidate, near_misses, rank_candidates
from football_platform.analytics.scouting_presets import PRESETS
from football_platform.database.connection import connect
from football_platform.reports.player_season_report import load_inputs

from phase6_validation import halves  # same split as the comparison validation

KIND = {m.key: m.kind for m in ALL_METRICS}


def percentile_column(key: str) -> str:
    return f"{key}_p90_pct" if KIND[key] is MetricKind.COUNT else f"{key}_pct"


def candidates(report, preset):
    pool = report[(report["position_group"] == preset.position_group.value) & report["eligible"]]
    return [
        Candidate(f"{r.player_id}:{r.season_id}", r.minutes,
                  tuple(None if np.isnan(r[percentile_column(c.metric_key)])
                        else float(r[percentile_column(c.metric_key)]) for c in preset.criteria))
        for _, r in pool.iterrows()
    ]


def later_performance(keys, second, preset):
    """(n tracked, share passing every criterion, mean criterion percentile) in the second half."""
    later = second.assign(k=second["player_id"] + ":" + second["season_id"]).set_index("k")
    later = later[later["eligible"] & (later["position_group"] == preset.position_group.value)]
    tracked = [k for k in keys if k in later.index]
    if not tracked:
        return 0, float("nan"), float("nan")
    rows = later.loc[tracked]
    columns = [percentile_column(c.metric_key) for c in preset.criteria]
    passed = np.all([rows[col] >= c.min_percentile for col, c in zip(columns, preset.criteria)], axis=0)
    return len(tracked), passed.mean(), np.nanmean(rows[columns].to_numpy())


def main() -> None:
    with connect() as conn:
        inputs = load_inputs(conn)
    first, second = halves(inputs)
    print("Second-half outcome of first-half selections (mean criterion percentile: 50 = average player)")
    print(f"{'preset':<26}{'shortlist':>10}{'pass':>7}{'mean pct':>10}{'near miss':>11}{'pass':>7}{'mean pct':>10}")
    for preset in PRESETS:
        pool = candidates(first, preset)
        short = [r.key for r in rank_candidates(pool, list(preset.criteria))]
        near = [c.key for c, _ in near_misses(pool, list(preset.criteria))]
        n1, pass1, pct1 = later_performance(short, second, preset)
        n2, pass2, pct2 = later_performance(near, second, preset)
        print(f"{preset.label:<26}{n1:>10}{pass1:>7.0%}{pct1:>10.0f}{n2:>11}{pass2:>7.0%}{pct2:>10.0f}")


if __name__ == "__main__":
    main()
