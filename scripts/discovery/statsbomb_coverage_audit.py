"""Coverage audit of StatsBomb Open Data competition-seasons.

Football question: for which competition-seasons is the data a *complete*
population of matches (valid for per-90 comparisons and percentiles), and
which contain only a subset, e.g. the matches of one team?

Evidence computed per competition-season (from match files only):
- number of matches and teams;
- focal-team share: share of matches involving the most frequent team.
  100 % means every match involves one team (single-team scope);
- matches per team (min / max). In a complete league season, every team plays
  about the same number of matches.

Classification heuristic (documented in docs/data/STATSBOMB_COVERAGE.md):
- single_team  : focal-team share == 100 % and more than one match;
- balanced     : min matches per team >= BALANCE_RATIO * max (league-like);
- unbalanced   : anything else (tournaments with knockouts, or partial data).
The heuristic only *flags*. Final coverage_scope is decided by review.

Output: a Markdown table on stdout and a JSON file in data/discovery/.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median
from typing import List

from statsbomb_download import PROJECT_ROOT, fetch_json, resolve_commit

BALANCE_RATIO = 0.9  # league: every team within 10 % of the max match count
OUTPUT_DIR = PROJECT_ROOT / "data" / "discovery"


@dataclass
class SeasonCoverage:
    competition_id: int
    season_id: int
    competition: str
    season: str
    gender: str
    is_international: bool
    n_matches: int
    n_teams: int
    focal_team: str
    focal_team_share: float
    min_matches_per_team: int
    median_matches_per_team: float
    max_matches_per_team: int
    has_360: bool
    flag: str


def classify(n_matches: int, focal_share: float, min_mpt: int, max_mpt: int) -> str:
    if n_matches > 1 and focal_share == 1.0:
        return "single_team"
    if n_matches > 1 and min_mpt >= BALANCE_RATIO * max_mpt:
        return "balanced"
    return "unbalanced"


def audit_season(entry: dict, commit: str) -> SeasonCoverage:
    competition_id = entry["competition_id"]
    season_id = entry["season_id"]
    matches = fetch_json(f"data/matches/{competition_id}/{season_id}.json", commit)

    appearances: Counter = Counter()
    for match in matches:
        appearances[match["home_team"]["home_team_name"]] += 1
        appearances[match["away_team"]["away_team_name"]] += 1

    focal_team, focal_count = appearances.most_common(1)[0]
    per_team = list(appearances.values())
    n_matches = len(matches)

    return SeasonCoverage(
        competition_id=competition_id,
        season_id=season_id,
        competition=entry["competition_name"],
        season=entry["season_name"],
        gender=entry["competition_gender"],
        is_international=bool(entry["competition_international"]),
        n_matches=n_matches,
        n_teams=len(appearances),
        focal_team=focal_team,
        focal_team_share=round(focal_count / n_matches, 3),
        min_matches_per_team=min(per_team),
        median_matches_per_team=median(per_team),
        max_matches_per_team=max(per_team),
        has_360=entry.get("match_available_360") is not None,
        flag=classify(n_matches, focal_count / n_matches, min(per_team), max(per_team)),
    )


def to_markdown(rows: List[SeasonCoverage]) -> str:
    header = (
        "| Competition | Season | Gender | Matches | Teams | Focal team (share) "
        "| Matches/team min–med–max | 360 | Flag |\n"
        "|---|---|---|---:|---:|---|---|---|---|"
    )
    lines = [header]
    for r in rows:
        lines.append(
            f"| {r.competition} | {r.season} | {r.gender} | {r.n_matches} | {r.n_teams} "
            f"| {r.focal_team} ({r.focal_team_share:.0%}) "
            f"| {r.min_matches_per_team}–{r.median_matches_per_team:g}–{r.max_matches_per_team} "
            f"| {'yes' if r.has_360 else ''} | {r.flag} |"
        )
    return "\n".join(lines)


def main() -> None:
    commit = resolve_commit()
    competitions = fetch_json("data/competitions.json", commit)
    rows = [audit_season(entry, commit) for entry in competitions]
    rows.sort(key=lambda r: (r.gender, r.competition, r.season))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "statsbomb_coverage.json"
    output_path.write_text(
        json.dumps({"commit": commit, "seasons": [asdict(r) for r in rows]}, indent=2)
    )

    print(f"StatsBomb open-data commit: {commit}\n")
    print(to_markdown(rows))
    print(f"\nTotal: {len(rows)} competition-seasons, {sum(r.n_matches for r in rows)} matches")


if __name__ == "__main__":
    main()
