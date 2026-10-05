"""Download StatsBomb Open Data files into the local raw store, pinned to a commit.

Phase 1B discovery helper (stdlib only). Not application code: the production
ingestion pipeline is built in Phase 2.

Files land in data/raw/statsbomb_open_data/<commit_sha>/data/... which is
gitignored (docs/DECISIONS.md D004). Already-downloaded files are reused.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Optional

REPO = "statsbomb/open-data"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = PROJECT_ROOT / "data" / "raw" / "statsbomb_open_data"
COMMIT_FILE = RAW_ROOT / "PINNED_COMMIT"

MAX_ATTEMPTS = 3
RETRY_DELAY_S = 2.0


def _http_get(url: str) -> bytes:
    last_error: Optional[Exception] = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                return response.read()
        except Exception as error:  # network errors are retried, then re-raised
            last_error = error
            if attempt < MAX_ATTEMPTS:
                time.sleep(RETRY_DELAY_S * attempt)
    raise RuntimeError(f"Failed to download {url}: {last_error}")


def resolve_commit(refresh: bool = False) -> str:
    """Return the pinned commit SHA, pinning the current master HEAD on first use."""
    if COMMIT_FILE.exists() and not refresh:
        return COMMIT_FILE.read_text().strip()
    payload = json.loads(_http_get(f"https://api.github.com/repos/{REPO}/commits/master"))
    sha = payload["sha"]
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    COMMIT_FILE.write_text(sha + "\n")
    return sha


def fetch_json(relative_path: str, commit: str) -> Any:
    """Return parsed JSON for a repo path such as 'data/competitions.json'."""
    local_path = RAW_ROOT / commit / relative_path
    if not local_path.exists():
        url = f"https://raw.githubusercontent.com/{REPO}/{commit}/{relative_path}"
        content = _http_get(url)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(content)
    with local_path.open(encoding="utf-8") as handle:
        return json.load(handle)


if __name__ == "__main__":
    pinned = resolve_commit(refresh="--refresh" in sys.argv)
    print(f"Pinned StatsBomb open-data commit: {pinned}")
    competitions = fetch_json("data/competitions.json", pinned)
    print(f"competitions.json: {len(competitions)} competition-seasons")
