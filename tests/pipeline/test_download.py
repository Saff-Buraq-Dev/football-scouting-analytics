from football_platform.pipeline.download_statsbomb import AUDITED_COMMIT, resolve_commit


def test_fresh_install_pins_the_audited_release_without_network(tmp_path):
    assert resolve_commit(tmp_path) == AUDITED_COMMIT
    assert (tmp_path / "PINNED_COMMIT").read_text().strip() == AUDITED_COMMIT


def test_existing_pin_is_kept(tmp_path):
    (tmp_path / "PINNED_COMMIT").write_text("abc123\n")
    assert resolve_commit(tmp_path) == "abc123"
