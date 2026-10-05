from football_platform.analytics.definitions import ALL_METRICS, PositionGroup
from football_platform.analytics.profile_templates import TEMPLATES

METRICS = {m.key: m for m in ALL_METRICS}


def test_every_position_group_has_a_template():
    assert set(TEMPLATES) == set(PositionGroup)


def test_templates_only_reference_known_metrics_valid_for_the_group():
    for group, themes in TEMPLATES.items():
        for keys in themes.values():
            for key in keys:
                assert key in METRICS, f"{group}: unknown metric {key}"
                allowed = METRICS[key].position_groups
                assert allowed is None or group.value in allowed, f"{key} is not defined for {group}"


def test_no_metric_is_shown_twice_in_a_profile():
    for group, themes in TEMPLATES.items():
        keys = [k for ks in themes.values() for k in ks]
        assert len(keys) == len(set(keys)), group
