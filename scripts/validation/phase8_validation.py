"""Validation of team metrics (docs/FOOTBALL_ANALYTICS.md, Phase 8).

1. Predictive value: which first-half-season measure best predicts second-half points per match?
2. Face validity: style extremes of 2015/16.

Run: cd scripts/validation && ../../.venv/bin/python phase8_validation.py
"""

from __future__ import annotations

import numpy as np

from football_platform.database.connection import connect
from football_platform.reports.player_season_report import query_frame
from football_platform.reports.team_season_report import compute_teams, load_team_inputs

PREDICTORS = {
    "points_per_match": "Points per match",
    "goal_diff_per_match": "Goal difference per match",
    "xpts_per_match": "Expected points per match",
    "npxg_diff_per_match": "npxG difference per match",
}


def main() -> None:
    with connect() as conn:
        inputs = load_team_inputs(conn)
        names = query_frame(conn, "SELECT id AS team_id, name AS team FROM teams")
    matches = inputs.matches.copy()
    matches["rank"] = matches.groupby("season_id")["match_date"].rank(method="first")
    last = matches.groupby("season_id")["rank"].transform("max")
    first = compute_teams(inputs, set(matches.loc[matches["rank"] <= last / 2, "id"]))
    second = compute_teams(inputs, set(matches.loc[matches["rank"] > last / 2, "id"]))
    both = first.merge(second, on=["team_id", "season_id"], suffixes=("_h1", "_h2"))

    print(f"1. Predicting second-half points per match ({len(both)} team-seasons)")
    target = both["points_per_match_h2"]
    for key, label in PREDICTORS.items():
        r = np.corrcoef(both[f"{key}_h1"], target)[0, 1]
        print(f"   {label:<30} r = {r:.2f}   (R² = {r * r:.2f})")

    full = compute_teams(inputs).merge(names, on="team_id")
    full["luck"] = full["points_per_match"] - full["xpts_per_match"]
    print("\n2. Face validity (full season)")
    for metric, label, ascending in [
        ("possession_pct", "Highest possession", False),
        ("ppda", "Most intense pressing (lowest PPDA)", True),
        ("counter_npxg_share", "Most counter-attack reliant", False),
        ("set_piece_npxg_share", "Most set-piece reliant", False),
        ("luck", "Points above expected (over-performers)", False),
        ("luck", "Points below expected (under-performers)", True),
    ]:
        top = full.sort_values(metric, ascending=ascending).head(5)
        values = ", ".join(f"{t} {v:.2f}" for t, v in zip(top["team"], top[metric]))
        print(f"   {label:<42} {values}")


if __name__ == "__main__":
    main()
