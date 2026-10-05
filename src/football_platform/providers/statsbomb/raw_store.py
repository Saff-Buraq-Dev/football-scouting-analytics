"""Read-only access to a local copy of StatsBomb Open Data.

Layout: <root>/<commit>/data/{competitions.json, matches/, lineups/, events/}.
The adapter never touches the network; downloading is the pipeline's job.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class RawFileMissingError(FileNotFoundError):
    pass


class StatsBombRawStore:
    def __init__(self, root: Path, commit: str) -> None:
        self.root = root
        self.commit = commit
        self.data_dir = root / commit / "data"

    def _read(self, relative_path: str) -> Any:
        path = self.data_dir / relative_path
        if not path.exists():
            raise RawFileMissingError(f"Raw StatsBomb file not found: {path}")
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)

    def competitions(self) -> list[dict[str, Any]]:
        return self._read("competitions.json")

    def matches(self, competition_id: int, season_id: int) -> list[dict[str, Any]]:
        return self._read(f"matches/{competition_id}/{season_id}.json")

    def events(self, match_id: int) -> list[dict[str, Any]]:
        return self._read(f"events/{match_id}.json")

    def lineups(self, match_id: int) -> list[dict[str, Any]]:
        return self._read(f"lineups/{match_id}.json")
