import pytest

from football_platform.analytics.possession import team_match_possession
from tests.analytics.builders import ev, events


def test_possession_is_the_share_of_passes_and_ignores_shootout():
    rows = [ev("pass", team="t1")] * 3 + [ev("pass", team="t2")] + [ev("pass", team="t2", period=5)] * 10
    poss = team_match_possession(events(*rows)).set_index("team_id")["possession_pct"]
    assert poss.to_dict() == {"t1": pytest.approx(75.0), "t2": pytest.approx(25.0)}
