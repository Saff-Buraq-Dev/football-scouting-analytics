import uuid

from football_platform.api.corners import build_corner_report, season_corners

H, A, M = (uuid.uuid4() for _ in range(3))


def row(id_, type_, team, minute, possession, **kw):
    base = {"id": id_, "match_id": M, "team_id": team, "period": 1, "time_s": minute * 60.0, "type": type_,
            "set_piece": None, "start_y": 68.0, "end_x": 94.0, "end_y": 34.0, "shot_outcome": None,
            "possession_id": possession, "xg": None, "home_team_id": H, "away_team_id": A}
    base.update(kw)
    return base


def test_team_corner_report_splits_for_and_against():
    rows = [row("c1", "pass", H, 10, "1", set_piece="corner"), row("s1", "shot", H, 10.2, "1", xg=0.2, shot_outcome="goal"),
            row("c2", "pass", A, 30, "5", set_piece="corner", end_x=80.0)]
    corners, pairs = season_corners(rows)
    report = build_corner_report(corners, pairs, str(H))
    assert report["for"]["corners"] == 1 and report["for"]["goals"] == 1
    assert report["for"]["xg_per_corner"] == 0.2
    assert report["against"]["corners"] == 1 and report["against"]["xg_per_corner"] == 0.0
    assert report["league"]["corners"] == 2 and report["league"]["per_match"] == 1.0  # 2 corners / 2 team-matches
