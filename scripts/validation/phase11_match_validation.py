"""Match page validation (docs/FOOTBALL_ANALYTICS.md, Phase 11.4-11.5), on every match.

1. Goals placed in the binned xG race reproduce every official score.
2. Passing networks: minutes covered before the first change, and passes per network.

Run: .venv/bin/python scripts/validation/phase11_match_validation.py
"""

from __future__ import annotations

import numpy as np

from football_platform.analytics.match_report import passing_network, period_lengths, xg_race
from football_platform.database.connection import connect
from football_platform.reports.player_season_report import query_frame

EVENTS = """SELECT e.match_id, e.period, e.time_s, e.team_id, e.player_id, e.type, e.outcome, e.shot_outcome,
                   e.card_type, e.pass_recipient_id, e.start_x, e.start_y, e.end_x, e.end_y, m.value AS xg
            FROM events e LEFT JOIN provider_metrics m ON m.event_id = e.id AND m.metric_key = 'xg'
            WHERE e.type IN ('shot', 'own_goal', 'period_end', 'pass', 'substitution', 'card')"""


def main() -> None:
    with connect() as conn:
        events = query_frame(conn, EVENTS)
        matches = query_frame(conn, "SELECT id, home_team_id, away_team_id, home_score, away_score FROM matches")
    mismatches, cutoffs, sizes = 0, [], []
    for match, ev in events.groupby("match_id"):
        info = matches[matches["id"] == match].iloc[0]
        lengths = period_lengths(ev)
        in_play = ev[ev["period"] != 5]
        race = xg_race(in_play[in_play["type"] == "shot"], in_play[in_play["type"] == "own_goal"], lengths,
                       info.home_team_id, info.away_team_id)
        goals = (sum(b["home_goals"] for b in race), sum(b["away_goals"] for b in race))
        mismatches += goals != (info.home_score, info.away_score)
        for team in (info.home_team_id, info.away_team_id):
            network = passing_network(ev[ev["team_id"] == team], lengths)
            cutoffs.append(network["cutoff_minute"])
            sizes.append(network["completed_passes"])
    n = matches.shape[0]
    print(f"1. Score reproduced by the xG race goals: {n - mismatches}/{n} matches")
    c, s = np.array(cutoffs), np.array(sizes)
    print(f"2. Networks ({len(c)}): minutes before first change median {np.median(c):.0f} "
          f"(10th pct {np.percentile(c, 10):.0f}); completed passes median {np.median(s):.0f} "
          f"(10th pct {np.percentile(s, 10):.0f}); under 100 passes: {(s < 100).mean():.1%}")


if __name__ == "__main__":
    main()
