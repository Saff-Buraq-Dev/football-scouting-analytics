"""StatsBomb lineups -> canonical players and appearances (docs/data/STATSBOMB_MAPPING.md §5-6).

Lineup spells use the match clock ("MM:SS"), which restarts at 45:00, 90:00 and
105:00 for periods 2-4. First-half stoppage time therefore overlaps the
second-half clock range, so clock values are converted to elapsed seconds per
period. A spell with no end ('to' is null) lasts until the end of the match,
taken from the Half End events (actual period lengths incl. stoppage time).

Data-quality rules (found by the minutes validation on Premier League 2015/16,
documented in docs/data/STATSBOMB_MAPPING.md §6):
- Lineup spells sometimes continue after a player was substituted off or sent
  off (e.g. via a later Tactical Shift). Substitution and dismissal *events*
  are treated as the source of truth: playing time is cut at the player's exit.
- Spells can overlap or run backwards in time; overlaps are trimmed so that no
  second is counted twice.
- Some starters carry start_reason "Tactical Shift": a starter is any player on
  the pitch at 00:00 of period 1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from football_platform.canonical.enums import EntityType
from football_platform.canonical.identifiers import internal_id
from football_platform.canonical.models import SHOOTOUT_PERIOD, Appearance, Player, PositionSpell
from football_platform.providers.statsbomb.constants import PROVIDER
from football_platform.providers.statsbomb.events import parse_timestamp
from football_platform.providers.statsbomb.positions import to_canonical_position

PERIOD_CLOCK_OFFSET_S = {1: 0, 2: 45 * 60, 3: 90 * 60, 4: 105 * 60, 5: 120 * 60}
DISMISSAL_CARDS = {"Red Card", "Second Yellow"}

# (period, seconds since period start)
MatchTime = tuple[int, float]


@dataclass
class LineupMappingResult:
    players: list[Player] = field(default_factory=list)
    appearances: list[Appearance] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def clock_to_seconds(clock: str) -> int:
    """'MM:SS' match clock -> seconds of match clock."""
    minutes, seconds = clock.split(":")
    return int(minutes) * 60 + int(seconds)


def clock_to_period_elapsed(clock: str, period: int) -> float:
    """Match-clock value in a given period -> seconds since that period started."""
    return float(max(clock_to_seconds(clock) - PERIOD_CLOCK_OFFSET_S[period], 0))


def split_spell(
    raw_spell: dict[str, Any], period_lengths_s: dict[int, float], warnings: list[str], label: str
) -> list[PositionSpell]:
    """Turn one StatsBomb position spell into per-period canonical spells."""
    position = to_canonical_position(raw_spell["position"])
    played_periods = sorted(p for p in period_lengths_s if p != SHOOTOUT_PERIOD)
    if not played_periods:
        raise ValueError("No period lengths available (missing Half End events)")

    start_period = raw_spell["from_period"]
    start_s = clock_to_period_elapsed(raw_spell["from"], start_period)
    if raw_spell.get("to") is None:
        end_period = played_periods[-1]
        end_s = period_lengths_s[end_period]
    else:
        end_period = raw_spell["to_period"]
        end_s = clock_to_period_elapsed(raw_spell["to"], end_period)

    spells: list[PositionSpell] = []
    for period in range(start_period, end_period + 1):
        if period == SHOOTOUT_PERIOD or period not in period_lengths_s:
            continue
        length = period_lengths_s[period]
        seg_start = start_s if period == start_period else 0.0
        seg_end = end_s if period == end_period else length
        if seg_end > length:
            warnings.append(f"{label}: spell end {seg_end:.0f}s beyond period {period} length {length:.0f}s; clamped")
            seg_end = length
        if seg_start > seg_end:
            warnings.append(f"{label}: spell start after end in period {period}; skipped")
            continue
        spells.append(PositionSpell(position, period, seg_start, seg_end))
    return spells


def exit_times_from_events(raw_events: list[dict[str, Any]]) -> dict[int, MatchTime]:
    """Earliest substitution-off or dismissal per StatsBomb player id."""
    exits: dict[int, MatchTime] = {}
    for event in raw_events:
        type_name = event["type"]["name"]
        player = event.get("player")
        if player is None or event["period"] == SHOOTOUT_PERIOD:
            continue
        card = None
        if type_name == "Foul Committed":
            card = (event.get("foul_committed", {}).get("card") or {}).get("name")
        elif type_name == "Bad Behaviour":
            card = (event.get("bad_behaviour", {}).get("card") or {}).get("name")
        if type_name == "Substitution" or card in DISMISSAL_CARDS:
            moment = (event["period"], parse_timestamp(event["timestamp"]))
            exits[player["id"]] = min(moment, exits.get(player["id"], moment))
    return exits


def normalise_spells(
    spells: list[PositionSpell], exit_time: MatchTime | None, warnings: list[str], label: str
) -> list[PositionSpell]:
    """Cut spells at the player's exit and remove overlaps between spells."""
    cleaned: list[PositionSpell] = []
    for spell in sorted(spells, key=lambda s: (s.period, s.start_s, s.end_s)):
        start, end = spell.start_s, spell.end_s
        if exit_time is not None:
            exit_period, exit_s = exit_time
            if spell.period > exit_period or (spell.period == exit_period and start >= exit_s):
                if end > start:
                    warnings.append(f"{label}: spell after exit removed (period {spell.period})")
                continue
            if spell.period == exit_period and end > exit_s:
                warnings.append(f"{label}: spell cut at exit (period {spell.period})")
                end = exit_s
        previous = cleaned[-1] if cleaned else None
        if previous is not None and previous.period == spell.period and start < previous.end_s:
            if end > previous.end_s:
                warnings.append(f"{label}: overlapping spells trimmed (period {spell.period})")
            start = previous.end_s
        if end > start:
            cleaned.append(PositionSpell(spell.position, spell.period, start, end))
    return cleaned


def map_lineups(
    raw_lineups: list[dict[str, Any]],
    match_id: str,
    period_lengths_s: dict[int, float],
    exit_times: dict[int, MatchTime] | None = None,
) -> LineupMappingResult:
    result = LineupMappingResult()
    for team in raw_lineups:
        team_id = internal_id(PROVIDER, EntityType.TEAM, team["team_id"])
        for raw_player in team["lineup"]:
            player_id = internal_id(PROVIDER, EntityType.PLAYER, raw_player["player_id"])
            country = raw_player.get("country")
            result.players.append(
                Player(
                    id=player_id,
                    name=raw_player["player_name"],
                    known_name=raw_player.get("player_nickname"),
                    nationality=country.get("name") if country else None,
                )
            )
            label = f"match {match_id} player {raw_player['player_id']}"
            raw_positions = raw_player.get("positions", [])
            spells: list[PositionSpell] = []
            for raw_spell in raw_positions:
                spells.extend(split_spell(raw_spell, period_lengths_s, result.warnings, label))
            exit_time = (exit_times or {}).get(raw_player["player_id"])
            spells = normalise_spells(spells, exit_time, result.warnings, label)
            result.appearances.append(
                Appearance(
                    match_id=match_id,
                    team_id=team_id,
                    player_id=player_id,
                    is_starter=any(p["from"] == "00:00" and p["from_period"] == 1 for p in raw_positions),
                    position_spells=tuple(spells),
                    shirt_number=raw_player.get("jersey_number"),
                )
            )
    return result
