"""The SQL CHECK constraints must accept exactly the canonical enum values."""

import re
from importlib import resources

import pytest

from football_platform.analytics.definitions import PositionGroup
from football_platform.canonical import enums

MIGRATIONS = resources.files("football_platform.database").joinpath("migrations")
SCHEMA = "\n".join(f.read_text() for f in sorted(MIGRATIONS.iterdir(), key=lambda f: f.name) if f.name.endswith(".sql"))

# (column as written in SQL) -> canonical enum. Columns sharing a name share a vocabulary.
COLUMN_ENUMS = {
    "gender": enums.Gender,
    "competition_type": enums.CompetitionType,
    "coverage_scope": enums.CoverageScope,
    "team_type": enums.TeamType,
    "status": enums.MatchStatus,
    "line": enums.PositionLine,
    "role": enums.PositionRole,
    "primary_role": enums.PositionRole,
    "position_group": PositionGroup,
    "side": enums.Side,
    "type": enums.EventType,
    "outcome": enums.Outcome,
    "body_part": enums.BodyPart,
    "set_piece": enums.SetPiece,
    "possession_origin": enums.PossessionOrigin,
    "duel_kind": enums.DuelKind,
    "pass_height": enums.PassHeight,
    "shot_outcome": enums.ShotOutcome,
    "goalkeeper_action_kind": enums.GoalkeeperActionKind,
    "card_type": enums.CardType,
    "entity_type": enums.EntityType,
}

CHECK_IN = re.compile(r"CHECK \((\w+) IN \(([^)]*)\)\)", re.S)


def check_constraints() -> list[tuple[str, set[str]]]:
    return [(col, set(re.findall(r"'([^']*)'", values))) for col, values in CHECK_IN.findall(SCHEMA)]


def test_every_enum_check_is_covered():
    columns = {col for col, _ in check_constraints()}
    assert columns == set(COLUMN_ENUMS), "Add new CHECK columns to COLUMN_ENUMS"


@pytest.mark.parametrize(("column", "allowed"), check_constraints(), ids=lambda v: v if isinstance(v, str) else "")
def test_check_values_match_canonical_enum(column, allowed):
    assert allowed == {member.value for member in COLUMN_ENUMS[column]}
