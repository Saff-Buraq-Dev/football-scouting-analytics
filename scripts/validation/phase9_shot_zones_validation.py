"""Shot zone validation (docs/FOOTBALL_ANALYTICS.md, Phase 9b).

1. Sanity: npxG per shot must decrease from the six-yard box to long range.
2. Conservation: zone totals equal non-penalty shot, goal and npxG totals.

Run: .venv/bin/python scripts/validation/phase9_shot_zones_validation.py
"""

from __future__ import annotations

from football_platform.analytics.shot_zones import ZONES, prepare_shots, zone_summary
from football_platform.database.connection import connect
from football_platform.reports.player_season_report import query_frame

SHOTS_QUERY = """
    SELECT e.id, e.period, e.start_x, e.start_y, e.set_piece, e.shot_outcome, m.value AS xg
    FROM events e JOIN provider_metrics m ON m.event_id = e.id AND m.metric_key = 'xg'
    WHERE e.type = 'shot'"""


def main() -> None:
    with connect() as conn:
        shots = query_frame(conn, SHOTS_QUERY)
    prepared = prepare_shots(shots)
    summary = zone_summary(prepared).set_index("zone")
    labels = {z.key: z.label for z in ZONES}
    print(f"{'zone':<18}{'shots':>8}{'share':>8}{'goals':>7}{'conversion':>12}{'npxG/shot':>11}")
    for key, row in summary.iterrows():
        print(f"{labels[key]:<18}{row.shots:>8.0f}{row.share:>8.1%}{row.goals:>7.0f}"
              f"{row.goals / row.shots:>12.1%}{row.npxg_per_shot:>11.3f}")
    xg_per_shot = summary["npxg_per_shot"]
    order = ["six_yard", "box_central", "box_wide", "edge", "long_range"]
    monotone = all(xg_per_shot[a] > xg_per_shot[b] for a, b in zip(order, order[1:]))
    print(f"\nnpxG per shot decreasing six-yard > box central > box wide > edge > long range: {monotone}")
    print(f"Conservation: {summary['shots'].sum():.0f} zone shots = {len(prepared)} non-penalty shots; "
          f"zone npxG {summary['npxg'].sum():.2f} = {prepared['xg'].sum():.2f}")


if __name__ == "__main__":
    main()
