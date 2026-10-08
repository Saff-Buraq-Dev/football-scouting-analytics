"""Validation of Expected Threat (docs/FOOTBALL_ANALYTICS.md, Phase 11.1).

1. Sanity of the fitted surface: threat rises towards goal and is roughly symmetric.
2. Predictive value for the player's own goal threat (pre-registered criterion).
3. Stability: is xT a repeatable player trait?
4. Team level: does team xT lead to chances (npxG), now and later?

Run: cd scripts/validation && ../../.venv/bin/python phase11_xt_validation.py
"""

from __future__ import annotations

import numpy as np

from football_platform.analytics.player_match import shot_xg
from football_platform.analytics.xt import fit_xt
from football_platform.database.connection import connect
from football_platform.reports.player_season_report import load_inputs

from phase6_validation import MIN_MINUTES_EACH_HALF, halves


def r2(y: np.ndarray, *features: np.ndarray) -> float:
    x = np.column_stack([np.ones_like(y), *features])
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    residual = y - x @ beta
    return 1 - residual.var() / y.var()


def main() -> None:
    with connect() as conn:
        inputs = load_inputs(conn)

    model = fit_xt(inputs.events, shot_xg(inputs.metrics))
    surface = model.matrix()  # rows across the width, columns towards the opponent goal
    by_column = surface.mean(axis=0)
    print(f"1. Surface fitted on {model.actions:,} open-play actions in {model.iterations} iterations")
    print("   mean xT by column (own goal -> opponent goal):", " ".join(f"{v:.3f}" for v in by_column))
    print(f"   rises towards goal over the last 6 columns: {bool(np.all(np.diff(by_column[-6:]) > 0))}")
    print(f"   max cell: {surface.max():.3f} | left/right asymmetry (mean abs diff vs mirrored): "
          f"{np.abs(surface - surface[::-1]).mean():.4f}")

    first, second = halves(inputs)  # compute() fits xT on each half's own events
    both = first.merge(second, on=["player_id", "season_id"], suffixes=("_1", "_2"))
    both = both[(both["minutes_1"] >= MIN_MINUTES_EACH_HALF) & (both["minutes_2"] >= MIN_MINUTES_EACH_HALF)
                & (both["position_group_1"] != "goalkeeper")]
    threat_2 = (both["npxg_p90_2"] + both["xa_p90_2"]).to_numpy()
    threat_1 = (both["npxg_p90_1"] + both["xa_p90_1"]).to_numpy()
    xt_1 = (both["xt_pass_p90_1"] + both["xt_carry_p90_1"]).to_numpy()
    key_1 = both["key_passes_p90_1"].to_numpy()
    xa_1 = both["xa_p90_1"].to_numpy()

    print(f"\n2. Predicting second-half npxG + xA per 90 ({len(both)} outfield players, >= "
          f"{MIN_MINUTES_EACH_HALF:.0f} min each half)")
    for label, x in [("xT per 90 (passes + carries)", xt_1), ("key passes per 90", key_1), ("xA per 90", xa_1),
                     ("npxG + xA per 90 (same metric)", threat_1)]:
        print(f"   {label:<34} r = {np.corrcoef(x, threat_2)[0, 1]:.2f}")
    base, extended = r2(threat_2, threat_1), r2(threat_2, threat_1, xt_1)
    print(f"   R² from first-half npxG + xA: {base:.3f}; adding xT: {extended:.3f} (+{extended - base:.3f})")
    what_xt_claims(inputs)


def what_xt_claims(inputs) -> None:
    """3. Stability (is xT a repeatable player trait?) and 4. team level (does it lead to chances?)."""
    from football_platform.analytics.player_match import player_match_stats

    first, second = halves(inputs)
    both = first.merge(second, on=["player_id", "season_id"], suffixes=("_1", "_2"))
    both = both[(both["minutes_1"] >= MIN_MINUTES_EACH_HALF) & (both["minutes_2"] >= MIN_MINUTES_EACH_HALF)
                & (both["position_group_1"] != "goalkeeper")]
    print("\n3. Stability: first-half vs second-half per 90, same player")
    for label, key in [("xT (passes + carries)", None), ("progressive passes", "progressive_passes"),
                       ("key passes", "key_passes"), ("npxG + xA", "threat")]:
        if key is None:
            a = both["xt_pass_p90_1"] + both["xt_carry_p90_1"]
            b = both["xt_pass_p90_2"] + both["xt_carry_p90_2"]
        elif key == "threat":
            a, b = both["npxg_p90_1"] + both["xa_p90_1"], both["npxg_p90_2"] + both["xa_p90_2"]
        else:
            a, b = both[f"{key}_p90_1"], both[f"{key}_p90_2"]
        print(f"   {label:<24} r = {np.corrcoef(a, b)[0, 1]:.2f}")

    matches = inputs.matches.copy()
    matches["rank"] = matches.groupby("season_id")["match_date"].rank(method="first")
    last = matches.groupby("season_id")["rank"].transform("max")
    split = {"1": set(matches.loc[matches["rank"] <= last / 2, "id"]), "2": set(matches.loc[matches["rank"] > last / 2, "id"])}
    team = {}
    for half, ids in split.items():
        events = inputs.events[inputs.events["match_id"].isin(ids)]
        model = fit_xt(events, shot_xg(inputs.metrics))
        pm = player_match_stats(events, inputs.metrics, inputs.spells[inputs.spells["match_id"].isin(ids)],
                                inputs.matches, model)
        pm = pm.merge(inputs.matches[["id", "season_id"]].rename(columns={"id": "match_id"}), on="match_id")
        per_team = pm.groupby(["season_id", "team_id"]).agg(
            xt=("xt_pass", "sum"), xt_carry=("xt_carry", "sum"), npxg=("npxg", "sum"), matches=("match_id", "nunique"))
        per_team["xt_pm"] = (per_team["xt"] + per_team["xt_carry"]) / per_team["matches"]
        per_team["npxg_pm"] = per_team["npxg"] / per_team["matches"]
        team[half] = per_team
    t = team["1"].join(team["2"], lsuffix="_1", rsuffix="_2")
    print(f"\n4. Team level ({len(t)} team-seasons, per match)")
    print(f"   same half: team xT vs team npxG                  r = {np.corrcoef(t['xt_pm_1'], t['npxg_pm_1'])[0, 1]:.2f}")
    print(f"   predicting second-half npxG from first-half xT   r = {np.corrcoef(t['xt_pm_1'], t['npxg_pm_2'])[0, 1]:.2f}")
    print(f"   predicting second-half npxG from first-half npxG r = {np.corrcoef(t['npxg_pm_1'], t['npxg_pm_2'])[0, 1]:.2f}")
    base, extended = r2(t["npxg_pm_2"].to_numpy(), t["npxg_pm_1"].to_numpy()), r2(
        t["npxg_pm_2"].to_numpy(), t["npxg_pm_1"].to_numpy(), t["xt_pm_1"].to_numpy())
    print(f"   R² second-half npxG: from npxG {base:.3f}; adding xT {extended:.3f} (+{extended - base:.3f})")


if __name__ == "__main__":
    main()
