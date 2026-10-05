"""Reproducible download of StatsBomb Open Data into the local raw store.

Files are pinned to one git commit of statsbomb/open-data and stored under
data/raw/statsbomb_open_data/<commit>/data/..., which is gitignored (D004).
Existing files are never re-downloaded, so the raw store is immutable per commit.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = "statsbomb/open-data"
MAX_ATTEMPTS = 4
RETRY_DELAY_S = 2.0
DEFAULT_WORKERS = 8

logger = logging.getLogger(__name__)


def _http_get(url: str) -> bytes:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(url, timeout=120) as response:
                return response.read()
        except OSError as error:
            if attempt == MAX_ATTEMPTS:
                raise RuntimeError(f"Failed to download {url} after {attempt} attempts") from error
            logger.warning("Retrying %s (%s)", url, error)
            time.sleep(RETRY_DELAY_S * attempt)
    raise AssertionError("unreachable")


def resolve_commit(raw_root: Path, refresh: bool = False) -> str:
    """Return the pinned commit, pinning the current master HEAD on first use."""
    pin_file = raw_root / "PINNED_COMMIT"
    if pin_file.exists() and not refresh:
        return pin_file.read_text().strip()
    sha = json.loads(_http_get(f"https://api.github.com/repos/{REPO}/commits/master"))["sha"]
    raw_root.mkdir(parents=True, exist_ok=True)
    pin_file.write_text(sha + "\n")
    logger.info("Pinned StatsBomb open data at commit %s", sha)
    return sha


def _download(raw_root: Path, commit: str, relative_path: str) -> bool:
    """Download one file if missing. Returns True when a download happened."""
    target = raw_root / commit / relative_path
    if target.exists():
        return False
    content = _http_get(f"https://raw.githubusercontent.com/{REPO}/{commit}/{relative_path}")
    json.loads(content)  # refuse to store anything that is not valid JSON
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".part")
    tmp.write_bytes(content)
    tmp.replace(target)
    return True


def download_seasons(
    raw_root: Path, commit: str, seasons: list[tuple[int, int]], workers: int = DEFAULT_WORKERS
) -> int:
    """Download competitions, match lists, events and lineups for the given seasons."""
    _download(raw_root, commit, "data/competitions.json")
    paths: list[str] = []
    for competition_id, season_id in seasons:
        matches_path = f"data/matches/{competition_id}/{season_id}.json"
        _download(raw_root, commit, matches_path)
        matches = json.loads((raw_root / commit / matches_path).read_text(encoding="utf-8"))
        for match in matches:
            paths.append(f"data/events/{match['match_id']}.json")
            paths.append(f"data/lineups/{match['match_id']}.json")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        downloaded = sum(pool.map(lambda p: _download(raw_root, commit, p), paths))
    logger.info("Raw store: %d files checked, %d downloaded", len(paths), downloaded)
    return downloaded
