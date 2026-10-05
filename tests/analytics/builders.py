"""Small canonical DataFrames for analytics tests (column names = canonical tables)."""

from __future__ import annotations

import itertools

import pandas as pd

from football_platform.analytics.player_match import EVENT_COLUMNS

_ids = itertools.count(1)


def ev(type_, player="p1", team="t1", match="m1", outcome="success", **kw):
    row = dict.fromkeys(EVENT_COLUMNS)
    row.update(id=f"e{next(_ids)}", match_id=match, period=1, team_id=team, player_id=player,
               type=type_, outcome=outcome)
    row.update(kw)
    return row


def events(*rows):
    return pd.DataFrame(list(rows), columns=list(EVENT_COLUMNS))


def metrics(*pairs, provider="statsbomb_open", version="statsbomb_xg"):
    return pd.DataFrame(
        [{"event_id": e, "metric_key": "xg", "value": v, "source_provider": provider, "model_version": version}
         for e, v in pairs],
        columns=["event_id", "metric_key", "value", "source_provider", "model_version"],
    )


SPELL_COLUMNS = ["match_id", "team_id", "player_id", "period", "start_s", "end_s", "role"]
MATCH_COLUMNS = ["id", "season_id", "home_team_id", "away_team_id"]


def spells(*rows):
    return pd.DataFrame(list(rows), columns=SPELL_COLUMNS)


def matches(*rows):
    return pd.DataFrame(list(rows) or [("m1", "s1", "t1", "t2"), ("m2", "s1", "t2", "t1")], columns=MATCH_COLUMNS)
