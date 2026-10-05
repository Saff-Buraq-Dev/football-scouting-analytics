"""Team possession proxy, shown as context next to defensive metrics.

A possession *adjustment* (PAdj) was evaluated and rejected (decision D017):
see docs/FOOTBALL_ANALYTICS.md, Phase 4.1 §2.
"""

from __future__ import annotations

import pandas as pd

from football_platform.canonical.enums import EventType
from football_platform.canonical.models import SHOOTOUT_PERIOD


def team_match_possession(events: pd.DataFrame) -> pd.DataFrame:
    """Possession % per (match, team) = team share of all passes attempted in the match."""
    passes = events[(events["type"] == EventType.PASS.value) & (events["period"] != SHOOTOUT_PERIOD)]
    counts = passes.groupby(["match_id", "team_id"]).size().rename("passes").reset_index()
    counts["possession_pct"] = counts["passes"] / counts.groupby("match_id")["passes"].transform("sum") * 100
    return counts[["match_id", "team_id", "possession_pct"]]
