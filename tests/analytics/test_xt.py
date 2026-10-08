import numpy as np
import pandas as pd
import pytest

from football_platform.analytics.pitch_grid import Grid
from football_platform.analytics.xt import action_values, fit_xt

COLUMNS = ["id", "period", "type", "outcome", "set_piece", "start_x", "start_y", "end_x", "end_y"]
GRID = Grid(columns=2, rows=1)  # two cells: own half (0) and opponent half (1)


def frame(rows):
    return pd.DataFrame(rows, columns=COLUMNS)


def test_grid_cells_and_missing_coordinates():
    grid = Grid(columns=16, rows=12)
    assert grid.cell(np.array([0.0, 104.99, np.nan]), np.array([0.0, 67.99, 10.0])).tolist() == [0, 191, -1]


def test_xt_solves_the_value_equation_on_a_hand_computable_pitch():
    # Opponent half: 1 shot (xG 0.5) and 1 successful move staying there -> s=0.5, m=0.5, T(1->1)=1.
    # Own half: 2 moves, 1 successful into the opponent half -> s=0, m=1, T(0->1)=0.5.
    events = frame([
        ("s1", 1, "shot", "fail", None, 80.0, 30.0, None, None),
        ("p1", 1, "pass", "success", None, 70.0, 30.0, 90.0, 30.0),
        ("p2", 1, "pass", "success", None, 20.0, 30.0, 60.0, 30.0),
        ("p3", 1, "pass", "fail", None, 20.0, 30.0, 70.0, 30.0),
        ("c1", 1, "pass", "success", "corner", 104.0, 0.0, 100.0, 34.0),  # set piece: ignored
    ])
    model = fit_xt(events, pd.Series({"s1": 0.5}), GRID)
    # x1 = 0.5*0.5 + 0.5*1*x1  ->  x1 = 0.5 ;  x0 = 1 * 0.5 * x1 = 0.25
    assert model.values == pytest.approx([0.25, 0.5], abs=1e-5)
    values = action_values(events, model)
    assert values.iloc[2] == pytest.approx(0.25, abs=1e-5)  # own half -> opponent half
    assert values.iloc[3] == 0.0  # failed pass: not valued in v1
    assert values.iloc[4] == 0.0  # set piece: not valued
    assert values.iloc[1] == pytest.approx(0.0, abs=1e-5)  # stays in the same cell


def test_backward_pass_has_negative_value():
    events = frame([
        ("s1", 1, "shot", "fail", None, 80.0, 30.0, None, None),
        ("p1", 1, "pass", "success", None, 70.0, 30.0, 20.0, 30.0),
        ("p2", 1, "pass", "success", None, 20.0, 30.0, 70.0, 30.0),
    ])
    model = fit_xt(events, pd.Series({"s1": 0.3}), GRID)
    assert action_values(events, model).iloc[1] < 0
