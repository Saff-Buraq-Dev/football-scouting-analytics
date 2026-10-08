import uuid

from football_platform.analytics.xt import XTModel
from football_platform.analytics.pitch_grid import Grid
from football_platform.api.match import build_match_report

M, H, A, P1, P2 = (uuid.uuid4() for _ in range(5))


def event(type_, team, player=None, minute=10.0, period=1, **kw):
    row = {"id": uuid.uuid4(), "match_id": M, "period": period, "time_s": minute * 60, "team_id": team,
           "player_id": player, "type": type_, "outcome": "success", "start_x": 60.0, "start_y": 34.0,
           "end_x": 95.0, "end_y": 34.0, "set_piece": None, "duel_kind": None, "aerial_won": None,
           "shot_outcome": None, "pass_is_shot_assist": None, "pass_is_goal_assist": None,
           "pass_assisted_shot_event_id": None, "goalkeeper_action_kind": None, "possession_origin": "regular_play",
           "pass_is_cross": None, "pass_recipient_id": None, "card_type": None}
    row.update(kw)
    return row


def test_report_uses_db_uuids_and_aggregates_team_totals():
    shot = event("shot", H, P1, minute=30, start_x=95.0, shot_outcome="goal")
    events = [shot, event("pass", H, P1, pass_recipient_id=P2), event("pass", H, P2, pass_recipient_id=P1),
              *[event("period_end", t, period=p, minute=45) for p in (1, 2) for t in (H, A)]]
    metrics = [{"event_id": shot["id"], "metric_key": "xg", "value": 0.4, "source_provider": "sb", "model_version": "v"}]
    apps = [{"match_id": M, "team_id": H, "player_id": p, "is_starter": True, "minutes_played": 90.0, "shirt_number": 9,
             "player_name": f"P{i}"} for i, p in enumerate((P1, P2))]
    match = {"id": M, "season_id": uuid.uuid4(), "home_team_id": H, "away_team_id": A, "home_team": "Home",
             "away_team": "Away", "home_score": 1, "away_score": 0}
    xt = XTModel.from_values(Grid(16, 12), [0.01] * 192)
    report = build_match_report(match, events, metrics, apps, [], xt)
    home = report["home"]
    assert home["passes"] == 2 and home["np_shots"] == 1  # team totals joined correctly (UUID vs str regression)
    assert home["npxg"] == 0.4 and report["xg_race"][-1]["home_xg"] == 0.4
    assert report["away"]["xpts"] < home["xpts"]
