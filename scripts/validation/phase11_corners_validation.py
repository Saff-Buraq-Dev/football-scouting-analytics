"""Corner analysis validation (docs/FOOTBALL_ANALYTICS.md, Phase 11.6).

1. Volume: corners per team per match.  2. Sanity: xG per corner by delivery zone.
3. Face validity: most and least dangerous corner teams per league (xG per corner, >= 100 corners).

Run: .venv/bin/python scripts/validation/phase11_corners_validation.py
"""

from __future__ import annotations

from football_platform.analytics.player_match import shot_xg
from football_platform.analytics.set_pieces import DELIVERY_ZONES, corner_outcomes, corner_summary
from football_platform.database.connection import connect
from football_platform.reports.player_season_report import query_frame

EVENTS = """SELECT e.id, e.match_id, e.team_id, e.period, e.time_s, e.type, e.set_piece, e.start_y, e.end_x, e.end_y,
                   e.shot_outcome, e.possession_id
            FROM events e WHERE e.type = 'shot' OR (e.type = 'pass' AND e.set_piece = 'corner')"""


def main() -> None:
    with connect() as conn:
        events = query_frame(conn, EVENTS)
        metrics = query_frame(conn, "SELECT event_id, metric_key, value, source_provider, model_version "
                                    "FROM provider_metrics")
        teams = query_frame(conn, """SELECT t.id AS team_id, t.name AS team FROM teams t""")
        seasons = query_frame(conn, """SELECT m.id AS match_id, c.name AS competition FROM matches m
                                       JOIN seasons s ON s.id = m.season_id JOIN competitions c ON c.id = s.competition_id""")
    corners = corner_outcomes(events, shot_xg(metrics)).merge(seasons, on="match_id").merge(teams, on="team_id")
    team_matches = corners.groupby(["team_id", "competition"])["match_id"].nunique().sum()
    overall = corner_summary(corners, team_matches)
    print(f"1. {overall['corners']:,} corners; {overall['per_match']:.2f} per team per match; "
          f"xG per corner {overall['xg_per_corner']:.3f}; shot within the possession {overall['shot_rate']:.1%}; "
          f"{overall['goals']} goals")
    print("\n2. By delivery zone:")
    for z in overall["zones"]:
        print(f"   {z['label']:<26} share {z['share']:6.1%}   xG per corner {z['xg_per_corner']:.3f}   "
              f"shot rate {z['shot_rate']:.1%}")
    print("\n3. xG per corner, teams with >= 100 corners:")
    for league, group in corners.groupby("competition"):
        per_team = group.groupby("team").agg(n=("id", "size"), xg=("xg", "mean"))
        per_team = per_team[per_team["n"] >= 100].sort_values("xg", ascending=False)
        top = ", ".join(f"{t} {v:.3f}" for t, v in per_team["xg"].head(3).items())
        low = ", ".join(f"{t} {v:.3f}" for t, v in per_team["xg"].tail(2).items())
        print(f"   {league:<16} top: {top} | lowest: {low}")


if __name__ == "__main__":
    main()
