"""Quantitative validation of the Phase 4.1 methods (docs/FOOTBALL_ANALYTICS.md, Phase 4.1).

1. Possession: evidence that the PAdj sigmoid over-corrects (why D017 keeps raw values + context).
2. Goalkeeping: are goals conceded by keepers conserved with goals scored?
3. Regressed estimates: do they predict the second half of a season better than raw first-half rates?

Run: .venv/bin/python scripts/validation/phase41_validation.py   (needs the loaded database)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from football_platform.analytics.player_match import player_match_stats
from football_platform.analytics.possession import team_match_possession
from football_platform.database.connection import connect
from football_platform.reports.player_season_report import compute, load_inputs

HALF_SEASON_MIN_MINUTES = 450.0  # threshold for the half-season prior population
MIN_MINUTES_EACH_HALF = 450.0  # players evaluated in the split-half test
SPLIT_HALF_METRICS = ["np_shots", "npxg", "key_passes", "xa", "progressive_passes",
                      "passes_into_box", "interceptions", "tackles", "aerials_won"]


def possession_context_check(inputs) -> None:
    """Evidence behind decision D017: the PAdj sigmoid over-corrects in these data."""
    pm = player_match_stats(inputs.events, inputs.metrics, inputs.spells, inputs.matches)
    poss = team_match_possession(inputs.events)
    team_match = pm.groupby(["match_id", "team_id"])[["tackles", "interceptions"]].sum().reset_index()
    team_match = team_match.merge(poss, on=["match_id", "team_id"])
    team_match["sigmoid"] = 2 / (1 + np.exp(-0.1 * (team_match["possession_pct"] - 50)))
    team_match = team_match.merge(
        inputs.matches[["id", "season_id"]].rename(columns={"id": "match_id"}), on="match_id"
    )
    raw = team_match["tackles"] + team_match["interceptions"]
    team_match["raw"], team_match["padj"] = raw, raw * team_match["sigmoid"]
    team = team_match.groupby(["season_id", "team_id"])[["possession_pct", "raw", "padj"]].mean()
    print("1. Possession — correlation with team defensive volume (80 team-seasons)")
    print(f"   raw tackles+interceptions:            r = {np.corrcoef(team['possession_pct'], team['raw'])[0, 1]:+.2f}")
    print(f"   with PAdj sigmoid (rejected, D017):   r = {np.corrcoef(team['possession_pct'], team['padj'])[0, 1]:+.2f}")


def goalkeeper_check(report: pd.DataFrame) -> None:
    conceded = report["gk_np_goals_conceded"].sum()
    scored = report["np_goals"].sum()
    gk_rows = report[report["position_group"] == "goalkeeper"]
    print("2. Goalkeeping — conservation")
    print(f"   non-penalty goals scored by players: {scored:.0f}")
    print(f"   non-penalty goals conceded by keepers: {gk_rows['gk_np_goals_conceded'].sum():.0f} "
          f"(all players with GK minutes: {conceded:.0f})")


def split_half_check(inputs) -> None:
    matches = inputs.matches.copy()
    matches["rank"] = matches.groupby("season_id")["match_date"].rank(method="first")
    matches["half"] = np.where(matches["rank"] <= matches.groupby("season_id")["rank"].transform("max") / 2, 1, 2)
    first = compute(inputs, HALF_SEASON_MIN_MINUTES, set(matches.loc[matches["half"] == 1, "id"]))
    second = compute(inputs, HALF_SEASON_MIN_MINUTES, set(matches.loc[matches["half"] == 2, "id"]))
    keys = ["player_id", "season_id"]
    both = first.merge(second, on=keys, suffixes=("_h1", "_h2"))
    both = both[(both["minutes_h1"] >= MIN_MINUTES_EACH_HALF) & (both["minutes_h2"] >= MIN_MINUTES_EACH_HALF)]
    print(f"3. Regressed estimates — predicting the second half from the first ({len(both)} player-seasons)")
    print(f"   {'metric':<22}{'RMSE raw':>10}{'RMSE regressed':>16}{'improvement':>13}")
    for m in SPLIT_HALF_METRICS:
        target = both[f"{m}_p90_h2"]
        weights = both["minutes_h2"]
        rmse = lambda pred: np.sqrt(np.average((pred - target) ** 2, weights=weights))  # noqa: E731
        raw, reg = rmse(both[f"{m}_p90_h1"]), rmse(both[f"{m}_p90_regressed_h1"])
        print(f"   {m:<22}{raw:>10.3f}{reg:>16.3f}{(1 - reg / raw):>12.0%}")


def main() -> None:
    with connect() as conn:
        inputs = load_inputs(conn)
    report = compute(inputs, 900.0)
    possession_context_check(inputs)
    goalkeeper_check(report)
    split_half_check(inputs)


if __name__ == "__main__":
    main()
