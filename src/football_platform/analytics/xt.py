"""Expected Threat (Karun Singh, 2018). Method: docs/FOOTBALL_ANALYTICS.md, "Phase 11.1".

xT(z) = s(z) g(z) + m(z) Σ T(z→z') xT(z'), solved by value iteration on a 16 × 12 grid.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from football_platform.analytics.pitch_grid import Grid
from football_platform.canonical.enums import EventType, Outcome
from football_platform.canonical.models import SHOOTOUT_PERIOD

XT_GRID = Grid(columns=16, rows=12)
CONVERGENCE = 1e-6
MAX_ITERATIONS = 1_000


@dataclass(frozen=True)
class XTModel:
    grid: Grid
    values: np.ndarray  # flat, one value per cell
    shot_probability: np.ndarray
    move_probability: np.ndarray
    goal_probability: np.ndarray
    iterations: int
    actions: int

    def matrix(self) -> np.ndarray:
        return self.grid.to_matrix(self.values)


def _open_play(events: pd.DataFrame) -> pd.DataFrame:
    return events[(events["period"] != SHOOTOUT_PERIOD) & events["set_piece"].isna()]


def _moves(ev: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """(is a move, is a successful move): passes with a known result, and carries."""
    is_pass = ev["type"] == EventType.PASS.value
    is_carry = ev["type"] == EventType.CARRY.value
    attempted_pass = is_pass & ev["outcome"].isin([Outcome.SUCCESS.value, Outcome.FAIL.value])
    move = attempted_pass | is_carry
    success = (is_pass & (ev["outcome"] == Outcome.SUCCESS.value)) | is_carry
    return move, success & ev["end_x"].notna() & ev["end_y"].notna()


def fit_xt(events: pd.DataFrame, shot_xg: pd.Series, grid: Grid = XT_GRID) -> XTModel:
    """Fit xT on open-play actions. shot_xg: provider xG indexed by shot event id."""
    ev = _open_play(events)
    ev = ev[ev["start_x"].notna() & ev["start_y"].notna()]
    start = grid.cell(ev["start_x"], ev["start_y"])
    is_shot = (ev["type"] == EventType.SHOT.value).to_numpy()
    move, success = (s.to_numpy() for s in _moves(ev))

    n = grid.cells
    shots = np.bincount(start[is_shot], minlength=n).astype(float)
    moves = np.bincount(start[move], minlength=n).astype(float)
    total = shots + moves
    safe_total = np.where(total > 0, total, 1.0)
    s = shots / safe_total
    m = moves / safe_total

    xg = ev["id"].map(shot_xg).to_numpy(dtype=float)
    xg_sum = np.bincount(start[is_shot], weights=np.nan_to_num(xg[is_shot]), minlength=n)
    g = np.where(shots > 0, xg_sum / np.where(shots > 0, shots, 1.0), 0.0)

    end = grid.cell(ev["end_x"], ev["end_y"])
    transitions = np.zeros((n, n))
    np.add.at(transitions, (start[success], end[success]), 1.0)
    transitions /= np.where(moves > 0, moves, 1.0)[:, None]  # rows sum to the success rate

    xt = np.zeros(n)
    for iteration in range(1, MAX_ITERATIONS + 1):
        updated = s * g + m * (transitions @ xt)
        if np.max(np.abs(updated - xt)) < CONVERGENCE:
            xt = updated
            break
        xt = updated
    return XTModel(grid, xt, s, m, g, iteration, int(total.sum()))


def action_values(events: pd.DataFrame, model: XTModel) -> pd.Series:
    """Net xT added by each successful open-play pass or carry (end − start); 0 for every other event."""
    values = pd.Series(0.0, index=events.index)
    open_play = (events["period"] != SHOOTOUT_PERIOD) & events["set_piece"].isna()
    _, success = _moves(events)
    valued = open_play & success & events["start_x"].notna() & events["start_y"].notna()
    if valued.any():
        sub = events[valued]
        start = model.grid.cell(sub["start_x"], sub["start_y"])
        end = model.grid.cell(sub["end_x"], sub["end_y"])
        values.loc[valued] = model.values[end] - model.values[start]
    return values
