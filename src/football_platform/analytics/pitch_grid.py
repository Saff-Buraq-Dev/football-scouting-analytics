"""Rectangular pitch grids on canonical coordinates (shared by xT and zone maps)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from football_platform.canonical.pitch import PITCH_LENGTH_M, PITCH_WIDTH_M


@dataclass(frozen=True, slots=True)
class Grid:
    columns: int  # along the pitch length (x), own goal -> opponent goal
    rows: int  # across the width (y)

    @property
    def cells(self) -> int:
        return self.columns * self.rows

    def column(self, x: pd.Series | np.ndarray) -> np.ndarray:
        return np.clip(np.floor(np.asarray(x, dtype=float) / PITCH_LENGTH_M * self.columns), 0, self.columns - 1)

    def row(self, y: pd.Series | np.ndarray) -> np.ndarray:
        return np.clip(np.floor(np.asarray(y, dtype=float) / PITCH_WIDTH_M * self.rows), 0, self.rows - 1)

    def cell(self, x: pd.Series | np.ndarray, y: pd.Series | np.ndarray) -> np.ndarray:
        """Flat cell index (row * columns + column); -1 where a coordinate is missing."""
        x_arr, y_arr = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
        index = self.row(y_arr) * self.columns + self.column(x_arr)
        return np.where(np.isnan(x_arr) | np.isnan(y_arr), -1, index).astype(int)

    def to_matrix(self, flat: np.ndarray) -> np.ndarray:
        """Flat per-cell values -> (rows, columns) matrix."""
        return np.asarray(flat, dtype=float).reshape(self.rows, self.columns)
