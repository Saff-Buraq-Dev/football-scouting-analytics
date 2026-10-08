"""Highest and lowest percentiles for the one-page scouting report (pure logic).

Rule (docs/FOOTBALL_ANALYTICS.md, "Phase 11.8 — One-page scouting report", D031): among the position template's
metrics, keep those with a percentile and a reliability of at least "medium" (regressed weight w >= 0.5, Phase 5).
With at least 2 x 3 such metrics, list the 3 highest and the 3 lowest percentiles; with fewer, a split would put
low percentiles under "highest" (goalkeepers have 2 count metrics), so they are listed once, ranked.
Ratios have no reliability estimate and are not candidates. The lists are descriptive ("highest percentiles"),
not a verdict ("strengths"): no percentile threshold is applied.
"""

from __future__ import annotations

from typing import Any

HIGHLIGHT_COUNT = 3
TRUSTED_BANDS = frozenset({"high", "medium"})


def highlights(themes: list[dict[str, Any]], count: int = HIGHLIGHT_COUNT) -> dict[str, Any]:
    """themes: the profile's themes (metric views).

    Returns {split, highest, lowest, ranked, low_reliability}: when split, highest/lowest hold `count` metrics each;
    otherwise every candidate is in `ranked` (highest first). low_reliability names the ranked metrics left out.
    """
    seen: dict[str, dict[str, Any]] = {}
    for theme in themes:
        for metric in theme["metrics"]:
            seen.setdefault(metric["key"], metric)

    ranked_metrics = [m for m in seen.values() if m["percentile"] is not None]
    candidates = [m for m in ranked_metrics if m["reliability_band"] in TRUSTED_BANDS]
    ranked = [_item(m) for m in sorted(candidates, key=lambda m: (-m["percentile"], m["key"]))]
    split = len(ranked) >= 2 * count
    return {
        "split": split,
        "highest": ranked[:count] if split else [],
        "lowest": ranked[::-1][:count] if split else [],
        "ranked": ranked,
        "low_reliability": [m["label"] for m in ranked_metrics if m["reliability_band"] == "low"],
    }


def _item(metric: dict[str, Any]) -> dict[str, Any]:
    return {"key": metric["key"], "label": metric["label"], "percentile": metric["percentile"],
            "reliability_band": metric["reliability_band"]}
