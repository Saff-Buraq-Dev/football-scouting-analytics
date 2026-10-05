"""Ingest StatsBomb Open Data seasons into canonical Parquet tables.

Usage:
    python -m football_platform.pipeline.ingest                 # D011 slice
    python -m football_platform.pipeline.ingest --season 2:27   # one season
    python -m football_platform.pipeline.ingest --skip-download

Output: data/canonical/statsbomb_open/<commit[:12]>/ with one Parquet file per
table and manifest.json (run metadata, counts, warnings, validation issues).
"""

from __future__ import annotations

import argparse
import json
import logging
import uuid
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from football_platform.canonical.enums import CoverageScope, EntityType
from football_platform.canonical.models import ExternalId
from football_platform.pipeline import storage
from football_platform.pipeline.download_statsbomb import download_seasons, resolve_commit
from football_platform.pipeline.validation import ValidationIssue, validate_bundle
from football_platform.providers.base import SeasonEntry
from football_platform.providers.statsbomb.adapter import StatsBombOpenDataAdapter
from football_platform.providers.statsbomb.constants import PROVIDER
from football_platform.providers.statsbomb.raw_store import StatsBombRawStore

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RAW_ROOT = PROJECT_ROOT / "data" / "raw" / "statsbomb_open_data"
DEFAULT_OUT_ROOT = PROJECT_ROOT / "data" / "canonical" / PROVIDER

# Decision D011: men's 2015/16 Premier League, La Liga, Serie A, Ligue 1.
D011_SLICE: list[tuple[int, int]] = [(2, 27), (11, 27), (12, 27), (7, 27)]
MAX_WARNINGS_IN_MANIFEST = 200

logger = logging.getLogger("football_platform.ingest")


def _parse_season(value: str) -> tuple[int, int]:
    competition_id, season_id = value.split(":")
    return int(competition_id), int(season_id)


def _provider_season_ref(entry: SeasonEntry) -> str:
    """StatsBomb 'competition_id:season_id' of a listed season, from its external ids."""
    return next(x.provider_id for x in entry.external_ids if x.entity_type is EntityType.SEASON)


def run(seasons: list[tuple[int, int]], raw_root: Path, out_root: Path, download: bool) -> dict[str, Any]:
    run_id = str(uuid.uuid4())
    started = datetime.now(timezone.utc)
    commit = resolve_commit(raw_root)
    if download:
        download_seasons(raw_root, commit, seasons)

    out_dir = out_root / commit[:12]
    adapter = StatsBombOpenDataAdapter(StatsBombRawStore(raw_root, commit), run_id)
    wanted = {f"{competition_id}:{season_id}" for competition_id, season_id in seasons}
    season_entries = [e for e in adapter.list_seasons() if _provider_season_ref(e) in wanted]
    if len(season_entries) != len(wanted):
        raise ValueError(f"Some requested seasons are not in competitions.json: {seasons}")

    competitions, teams, players = {}, {}, {}
    external_ids: dict[tuple[str, str, str], ExternalId] = {}
    matches = []
    warnings: list[str] = []
    issues: list[ValidationIssue] = []
    season_summaries = []
    writer = storage.IncrementalWriter(out_dir)
    try:
        for entry in season_entries:
            if entry.season.coverage_scope is not CoverageScope.COMPLETE:
                logger.warning("%s %s has coverage %s", entry.competition.name, entry.season.label,
                               entry.season.coverage_scope.value)
            competitions[entry.competition.id] = entry.competition
            external_ids.update({(x.entity_type, x.internal_id, x.provider): x for x in entry.external_ids})
            match_entries = adapter.list_matches(entry.season)
            season_issues_before = len(issues)
            for index, match_entry in enumerate(match_entries, start=1):
                bundle = adapter.load_match(match_entry.match)
                matches.append(match_entry.match)
                for team in (match_entry.home_team, match_entry.away_team):
                    teams.setdefault(team.id, team)
                for player in bundle.players:
                    players.setdefault(player.id, player)
                for x in (*match_entry.external_ids, *bundle.external_ids):
                    external_ids[(x.entity_type, x.internal_id, x.provider)] = x
                warnings.extend(bundle.warnings)
                issues.extend(validate_bundle(bundle))

                writer.append("events", [storage.event_row(e) for e in bundle.events])
                writer.append("provider_metrics", [r for e in bundle.events for r in storage.metric_rows(e)])
                writer.append("appearances", [storage.appearance_row(a) for a in bundle.appearances])
                writer.append("position_spells", [r for a in bundle.appearances for r in storage.spell_rows(a)])
                if index % 50 == 0:
                    logger.info("%s %s: %d/%d matches", entry.competition.name, entry.season.label,
                                index, len(match_entries))
            season_summaries.append({
                "competition": entry.competition.name,
                "season": entry.season.label,
                "coverage_scope": entry.season.coverage_scope.value,
                "matches": len(match_entries),
                "validation_issues": len(issues) - season_issues_before,
            })
            logger.info("Done %s %s: %d matches", entry.competition.name, entry.season.label, len(match_entries))
    finally:
        writer.close()

    counts = dict(writer.row_counts)
    counts["competitions"] = storage.write_table(out_dir, "competitions", map(storage.entity_row, competitions.values()))
    counts["seasons"] = storage.write_table(out_dir, "seasons", (storage.entity_row(e.season) for e in season_entries))
    counts["teams"] = storage.write_table(out_dir, "teams", map(storage.entity_row, teams.values()))
    counts["players"] = storage.write_table(out_dir, "players", map(storage.entity_row, players.values()))
    counts["matches"] = storage.write_table(out_dir, "matches", map(storage.entity_row, matches))
    counts["external_ids"] = storage.write_table(out_dir, "external_ids", map(storage.entity_row, external_ids.values()))

    manifest = {
        "ingestion_run_id": run_id,
        "provider": PROVIDER,
        "source_release": commit,
        "started_utc": started.isoformat(),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "capabilities": adapter.capabilities().to_dict(),
        "seasons": season_summaries,
        "row_counts": counts,
        "warnings_total": len(warnings),
        "warnings_by_kind": dict(Counter(w.split(": ", 1)[1].split(" '")[0] for w in warnings if ": " in w).most_common(20)),
        "warnings_sample": warnings[:MAX_WARNINGS_IN_MANIFEST],
        "validation_issues_total": len(issues),
        "validation_issues_by_check": dict(Counter(i.check for i in issues)),
        "validation_issues": [asdict(issue) for issue in issues],
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--season", action="append", type=_parse_season,
                        help="competition_id:season_id (repeatable). Default: D011 slice")
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    parser.add_argument("--skip-download", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    manifest = run(args.season or D011_SLICE, args.raw_root, args.out_root, download=not args.skip_download)
    print(json.dumps({k: manifest[k] for k in ("seasons", "row_counts", "warnings_total",
                                                "validation_issues_by_check")}, indent=2))


if __name__ == "__main__":
    main()
