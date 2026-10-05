from football_platform.analytics.goalkeeping import goalkeeper_match_stats
from tests.analytics.builders import ev, events, matches, spells

# t2 attacks t1's goal. Keeper "gk1" until 60:00 of period 2, then "gk2".
KEEPERS = spells(
    ("m1", "t1", "gk1", 1, 0, 2800, "GK"),
    ("m1", "t1", "gk1", 2, 0, 900, "GK"),
    ("m1", "t1", "gk2", 2, 900, 2900, "GK"),
    ("m1", "t2", "gk9", 1, 0, 2800, "GK"),
)


def shot(outcome, time_s, period=1, set_piece=None, team="t2"):
    return ev("shot", team=team, player="striker", shot_outcome=outcome, time_s=time_s, period=period,
              set_piece=set_piece)


def test_shots_are_attributed_to_the_keeper_on_the_pitch():
    rows = [shot("saved", 100), shot("goal", 200), shot("saved", 1000, period=2)]
    stats = goalkeeper_match_stats(events(*rows), KEEPERS, matches()).set_index("player_id")
    assert stats.loc["gk1", ["gk_np_sot_faced", "gk_np_goals_conceded", "gk_np_saves"]].tolist() == [2, 1, 1]
    assert stats.loc["gk2", "gk_np_saves"] == 1
    assert stats.loc["gk1", "team_id"] == "t1"


def test_penalties_off_target_shots_and_shootouts_are_excluded():
    rows = [shot("goal", 100, set_piece="penalty"), shot("off_target", 150), shot("blocked", 160),
            shot("saved", 10, period=5)]
    assert goalkeeper_match_stats(events(*rows), KEEPERS, matches()).empty


def test_shot_at_the_exact_keeper_change_is_counted_once():
    stats = goalkeeper_match_stats(events(shot("saved", 900, period=2)), KEEPERS, matches())
    assert stats["gk_np_sot_faced"].sum() == 1
