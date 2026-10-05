"""Profile the StatsBomb event, lineup and 360 schemas on a sample of matches.

Football question: which actions, attributes and positions does the source
actually record, and how complete are they? The answer drives the data
dictionary and the StatsBomb -> canonical mapping (docs/data/).

Sample: the first SAMPLE_PER_SEASON matches (by match_id) of each season in
SAMPLE_SEASONS. The sample is for *schema discovery*, not for statistics.

Output: data/discovery/statsbomb_profile.json and a summary on stdout.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any, Dict, List, Tuple

from statsbomb_download import PROJECT_ROOT, fetch_json, resolve_commit

# (competition_id, season_id, label). Chosen to cover complete men's and women's
# leagues and a tournament with 360 data.
SAMPLE_SEASONS: List[Tuple[int, int, str]] = [
    (2, 27, "Premier League 2015/16"),
    (11, 27, "La Liga 2015/16"),
    (12, 27, "Serie A 2015/16"),
    (37, 281, "FA WSL 2023/24"),
    (43, 106, "FIFA World Cup 2022"),
    (55, 282, "UEFA Euro 2024"),
]
SAMPLE_PER_SEASON = 2

# Keys present on every event; type-specific detail lives under the key named
# after the event type (e.g. event["pass"]).
COMMON_KEYS = {
    "id", "index", "period", "timestamp", "minute", "second", "type",
    "possession", "possession_team", "play_pattern", "team", "player",
    "position", "location", "duration", "under_pressure", "off_camera", "out",
    "related_events", "tactics", "counterpress",
}
ENUM_PATHS = {
    "pass.type", "pass.outcome", "pass.height", "pass.body_part", "pass.technique",
    "shot.type", "shot.outcome", "shot.body_part", "shot.technique",
    "dribble.outcome", "duel.type", "duel.outcome", "goalkeeper.type",
    "goalkeeper.outcome", "interception.outcome", "foul_committed.card",
    "bad_behaviour.card", "substitution.outcome", "clearance.body_part",
    "ball_receipt.outcome",
}


def flatten(prefix: str, value: Any, out: Dict[str, Any]) -> None:
    """Flatten nested dicts into dotted paths. {id, name} objects stop at the path."""
    if isinstance(value, dict) and not ({"id", "name"} <= set(value) and len(value) == 2):
        for key, sub in value.items():
            flatten(f"{prefix}.{key}" if prefix else key, sub, out)
    else:
        out[prefix] = value


def main() -> None:
    commit = resolve_commit()
    type_counts: Counter = Counter()
    attr_counts: Dict[str, Counter] = defaultdict(Counter)
    enum_values: Dict[str, Counter] = defaultdict(Counter)
    play_patterns: Counter = Counter()
    common_presence: Counter = Counter()
    positions: Counter = Counter()
    lineup_keys: Counter = Counter()
    position_keys: Counter = Counter()
    position_reasons: Counter = Counter()
    player_keys: Counter = Counter()
    period_ends: List[Dict[str, Any]] = []
    freeze_frame_stats = Counter()
    n_events = 0
    matches_used: List[str] = []

    for competition_id, season_id, label in SAMPLE_SEASONS:
        matches = fetch_json(f"data/matches/{competition_id}/{season_id}.json", commit)
        matches.sort(key=lambda m: m["match_id"])
        for match in matches[:SAMPLE_PER_SEASON]:
            match_id = match["match_id"]
            matches_used.append(
                f"{label}: {match['home_team']['home_team_name']} v "
                f"{match['away_team']['away_team_name']} ({match_id})"
            )
            events = fetch_json(f"data/events/{match_id}.json", commit)
            for event in events:
                n_events += 1
                event_type = event["type"]["name"]
                type_counts[event_type] += 1
                play_patterns[event["play_pattern"]["name"]] += 1
                for key in event:
                    if key in COMMON_KEYS:
                        common_presence[(event_type, key)] += 1
                for key, detail in event.items():
                    if key in COMMON_KEYS:
                        continue
                    flat: Dict[str, Any] = {}
                    flatten(key, detail, flat)
                    for path, value in flat.items():
                        attr_counts[event_type][path] += 1
                        if path in ENUM_PATHS:
                            name = value["name"] if isinstance(value, dict) else value
                            enum_values[path][name] += 1
                if event_type == "Half End":
                    period_ends.append(
                        {"match_id": match_id, "period": event["period"],
                         "timestamp": event["timestamp"], "minute": event["minute"],
                         "team": event["team"]["name"]}
                    )

            for team in fetch_json(f"data/lineups/{match_id}.json", commit):
                lineup_keys.update(team.keys())
                for player in team["lineup"]:
                    player_keys.update(player.keys())
                    for spell in player["positions"]:
                        position_keys.update(spell.keys())
                        positions[spell["position"]] += 1
                        position_reasons[("start", spell.get("start_reason"))] += 1
                        position_reasons[("end", spell.get("end_reason"))] += 1

            if match.get("match_status_360") == "available":
                frames = fetch_json(f"data/three-sixty/{match_id}.json", commit)
                freeze_frame_stats["matches"] += 1
                freeze_frame_stats["frames"] += len(frames)
                for frame in frames:
                    freeze_frame_stats["players_in_frames"] += len(frame["freeze_frame"])
                    for key in frame:
                        freeze_frame_stats[f"frame_key:{key}"] += 1
                    for item in frame["freeze_frame"][:1]:
                        for key in item:
                            freeze_frame_stats[f"player_key:{key}"] += 1

    profile = {
        "commit": commit,
        "matches": matches_used,
        "n_events": n_events,
        "event_types": dict(type_counts.most_common()),
        "play_patterns": dict(play_patterns.most_common()),
        "common_key_fill_rate": {
            f"{t}.{k}": round(c / type_counts[t], 3) for (t, k), c in sorted(common_presence.items())
        },
        "type_attributes_fill_rate": {
            t: {p: round(c / type_counts[t], 3) for p, c in sorted(attrs.items())}
            for t, attrs in sorted(attr_counts.items())
        },
        "enum_values": {p: dict(v.most_common()) for p, v in sorted(enum_values.items())},
        "lineup_team_keys": dict(lineup_keys),
        "lineup_player_keys": dict(player_keys),
        "lineup_position_keys": dict(position_keys),
        "positions": dict(positions.most_common()),
        "position_reasons": {f"{k[0]}:{k[1]}": v for k, v in position_reasons.most_common()},
        "period_ends": period_ends,
        "freeze_frames": dict(freeze_frame_stats),
    }
    output = PROJECT_ROOT / "data" / "discovery" / "statsbomb_profile.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(profile, indent=2, default=str))

    print(f"Commit {commit}: {len(matches_used)} matches, {n_events} events")
    print("\nEvent types:")
    for name, count in type_counts.most_common():
        print(f"  {name:<22} {count:>6}  {count / n_events:6.1%}")
    print(f"\nProfile written to {output.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
