"""Pressing metrics validation (docs/FOOTBALL_ANALYTICS.md, Phase 11.3).

Defensive height and final-third ball wins should agree with PPDA (lower PPDA = more intense pressing),
within each league. Run: .venv/bin/python scripts/validation/phase11_pressing_validation.py
"""

from __future__ import annotations

import numpy as np

from football_platform.database.connection import connect
from football_platform.reports.player_season_report import query_frame
from football_platform.reports.team_season_report import compute_teams, load_team_inputs


def main() -> None:
    with connect() as conn:
        inputs = load_team_inputs(conn)
        names = query_frame(conn, """SELECT t.id AS team_id, t.name AS team FROM teams t""")
        leagues = query_frame(conn, """SELECT s.id AS season_id, c.name AS competition
                                       FROM seasons s JOIN competitions c ON c.id = s.competition_id""")
    teams = compute_teams(inputs).merge(names, on="team_id").merge(leagues, on="season_id")
    print("Correlation with PPDA (expected negative), per league:")
    for league, group in teams.groupby("competition"):
        r_height = np.corrcoef(group["ppda"], group["defensive_height_m"])[0, 1]
        r_wins = np.corrcoef(group["ppda"], group["high_ball_wins_per_match"])[0, 1]
        print(f"  {league:<16} defensive height r = {r_height:+.2f}   high ball wins r = {r_wins:+.2f}")
    print("\nHighest and lowest defensive height per league (m from own goal):")
    for league, group in teams.groupby("competition"):
        ordered = group.sort_values("defensive_height_m", ascending=False)
        high = ", ".join(f"{t} {v:.1f}" for t, v in zip(ordered.team.head(3), ordered.defensive_height_m.head(3)))
        low = ", ".join(f"{t} {v:.1f}" for t, v in zip(ordered.team.tail(3), ordered.defensive_height_m.tail(3)))
        print(f"  {league:<16} high: {high}\n  {'':<16} low:  {low}")


if __name__ == "__main__":
    main()
