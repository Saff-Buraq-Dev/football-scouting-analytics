"""Write canonical records to Parquet tables with explicit schemas.

Layout: <out_dir>/<table>.parquet, plus events/position_spells/appearances
written incrementally (one row group per match) to bound memory use.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable

import pyarrow as pa
import pyarrow.parquet as pq

from football_platform.canonical.models import (
    Appearance,
    Competition,
    Event,
    ExternalId,
    Match,
    Player,
    Season,
    Team,
)

STR, F64, I64, BOOL = pa.string(), pa.float64(), pa.int64(), pa.bool_()

SCHEMAS: dict[str, pa.Schema] = {
    "competitions": pa.schema([
        ("id", STR), ("name", STR), ("area", STR), ("gender", STR),
        ("competition_type", STR), ("is_youth", BOOL), ("tier", I64),
    ]),
    "seasons": pa.schema([
        ("id", STR), ("competition_id", STR), ("label", STR), ("coverage_scope", STR),
        ("has_events", BOOL), ("has_lineups", BOOL), ("has_freeze_frames", BOOL),
        ("coverage_note", STR), ("start_date", pa.date32()), ("end_date", pa.date32()),
    ]),
    "teams": pa.schema([
        ("id", STR), ("name", STR), ("team_type", STR), ("gender", STR), ("area", STR), ("short_name", STR),
    ]),
    "players": pa.schema([
        ("id", STR), ("name", STR), ("known_name", STR), ("nationality", STR),
        ("birth_date", pa.date32()), ("height_cm", F64), ("preferred_foot", STR),
    ]),
    "matches": pa.schema([
        ("id", STR), ("season_id", STR), ("competition_id", STR), ("match_date", pa.date32()),
        ("home_team_id", STR), ("away_team_id", STR), ("home_score", I64), ("away_score", I64),
        ("status", STR), ("kickoff_time", pa.time64("us")), ("stage", STR), ("matchweek", I64),
        ("venue", STR), ("referee", STR),
    ]),
    "appearances": pa.schema([
        ("match_id", STR), ("team_id", STR), ("player_id", STR), ("is_starter", BOOL),
        ("shirt_number", I64), ("minutes_played", F64),
    ]),
    "position_spells": pa.schema([
        ("match_id", STR), ("team_id", STR), ("player_id", STR), ("period", I64),
        ("start_s", F64), ("end_s", F64), ("line", STR), ("role", STR), ("side", STR),
    ]),
    "events": pa.schema([
        ("id", STR), ("match_id", STR), ("period", I64), ("time_s", F64), ("team_id", STR),
        ("player_id", STR), ("type", STR), ("outcome", STR),
        ("start_x", F64), ("start_y", F64), ("end_x", F64), ("end_y", F64),
        ("body_part", STR), ("set_piece", STR), ("possession_origin", STR), ("possession_id", STR),
        ("duel_kind", STR), ("aerial_won", BOOL), ("under_pressure", BOOL),
        ("related_event_ids", pa.list_(STR)),
        ("pass_height", STR), ("pass_recipient_id", STR), ("pass_is_cross", BOOL),
        ("pass_is_switch", BOOL), ("pass_is_cut_back", BOOL), ("pass_is_through_ball", BOOL),
        ("pass_is_shot_assist", BOOL), ("pass_is_goal_assist", BOOL), ("pass_assisted_shot_event_id", STR),
        ("shot_outcome", STR), ("shot_technique", STR), ("shot_is_first_time", BOOL),
        ("shot_key_pass_event_id", STR), ("shot_end_z", F64),
        ("goalkeeper_action_kind", STR), ("card_type", STR), ("substitute_player_id", STR),
        ("provider_event_type", STR), ("provider_qualifiers", STR),
        ("source_provider", STR), ("source_record_id", STR), ("source_release", STR), ("ingestion_run_id", STR),
    ]),
    "provider_metrics": pa.schema([
        ("event_id", STR), ("match_id", STR), ("metric_key", STR), ("value", F64),
        ("source_provider", STR), ("model_version", STR),
    ]),
    "external_ids": pa.schema([
        ("entity_type", STR), ("internal_id", STR), ("provider", STR), ("provider_id", STR),
    ]),
}

INCREMENTAL_TABLES = ("events", "provider_metrics", "appearances", "position_spells")


def _plain(record: Any) -> dict[str, Any]:
    """Dataclass -> dict with enum members turned into their string values."""
    return {k: (v.value if hasattr(v, "value") else v) for k, v in asdict(record).items()}


def entity_row(record: Competition | Season | Team | Player | Match | ExternalId) -> dict[str, Any]:
    return _plain(record)


def event_row(event: Event) -> dict[str, Any]:
    p, s = event.pass_detail, event.shot_detail
    return {
        "id": event.id, "match_id": event.match_id, "period": event.period, "time_s": event.time_s,
        "team_id": event.team_id, "player_id": event.player_id,
        "type": event.type.value, "outcome": event.outcome.value,
        "start_x": event.start.x if event.start else None, "start_y": event.start.y if event.start else None,
        "end_x": event.end.x if event.end else None, "end_y": event.end.y if event.end else None,
        "body_part": event.body_part.value if event.body_part else None,
        "set_piece": event.set_piece.value if event.set_piece else None,
        "possession_origin": event.possession_origin.value if event.possession_origin else None,
        "possession_id": event.possession_id,
        "duel_kind": event.duel_kind.value if event.duel_kind else None,
        "aerial_won": event.aerial_won, "under_pressure": event.under_pressure,
        "related_event_ids": list(event.related_event_ids),
        "pass_height": p.height.value if p and p.height else None,
        "pass_recipient_id": p.recipient_id if p else None,
        "pass_is_cross": p.is_cross if p else None, "pass_is_switch": p.is_switch if p else None,
        "pass_is_cut_back": p.is_cut_back if p else None,
        "pass_is_through_ball": p.is_through_ball if p else None,
        "pass_is_shot_assist": p.is_shot_assist if p else None,
        "pass_is_goal_assist": p.is_goal_assist if p else None,
        "pass_assisted_shot_event_id": p.assisted_shot_event_id if p else None,
        "shot_outcome": s.outcome.value if s else None, "shot_technique": s.technique if s else None,
        "shot_is_first_time": s.is_first_time if s else None,
        "shot_key_pass_event_id": s.key_pass_event_id if s else None, "shot_end_z": s.end_z if s else None,
        "goalkeeper_action_kind": event.goalkeeper_action_kind.value if event.goalkeeper_action_kind else None,
        "card_type": event.card_type.value if event.card_type else None,
        "substitute_player_id": event.substitute_player_id,
        "provider_event_type": event.provider_event_type,
        "provider_qualifiers": json.dumps(event.provider_qualifiers, sort_keys=True) if event.provider_qualifiers else None,
        "source_provider": event.provenance.source_provider,
        "source_record_id": event.provenance.source_record_id,
        "source_release": event.provenance.source_release,
        "ingestion_run_id": event.provenance.ingestion_run_id,
    }


def metric_rows(event: Event) -> list[dict[str, Any]]:
    return [
        {"event_id": event.id, "match_id": event.match_id, "metric_key": m.metric_key, "value": m.value,
         "source_provider": m.source_provider, "model_version": m.model_version}
        for m in event.provider_metrics
    ]


def appearance_row(appearance: Appearance) -> dict[str, Any]:
    return {
        "match_id": appearance.match_id, "team_id": appearance.team_id, "player_id": appearance.player_id,
        "is_starter": appearance.is_starter, "shirt_number": appearance.shirt_number,
        "minutes_played": appearance.minutes_played,
    }


def spell_rows(appearance: Appearance) -> list[dict[str, Any]]:
    return [
        {"match_id": appearance.match_id, "team_id": appearance.team_id, "player_id": appearance.player_id,
         "period": spell.period, "start_s": spell.start_s, "end_s": spell.end_s,
         "line": spell.position.line.value,
         "role": spell.position.role.value if spell.position.role else None,
         "side": spell.position.side.value if spell.position.side else None}
        for spell in appearance.position_spells
    ]


def write_table(out_dir: Path, name: str, rows: Iterable[dict[str, Any]]) -> int:
    table = pa.Table.from_pylist(list(rows), schema=SCHEMAS[name])
    out_dir.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, out_dir / f"{name}.parquet")
    return table.num_rows


class IncrementalWriter:
    """Appends one row group per call; used for the large per-match tables."""

    def __init__(self, out_dir: Path) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        self._writers = {
            name: pq.ParquetWriter(out_dir / f"{name}.parquet", SCHEMAS[name]) for name in INCREMENTAL_TABLES
        }
        self.row_counts = dict.fromkeys(INCREMENTAL_TABLES, 0)

    def append(self, name: str, rows: list[dict[str, Any]]) -> None:
        if rows:
            self._writers[name].write_table(pa.Table.from_pylist(rows, schema=SCHEMAS[name]))
            self.row_counts[name] += len(rows)

    def close(self) -> None:
        for writer in self._writers.values():
            writer.close()
