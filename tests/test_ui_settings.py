"""User-config UI settings path, migration, and session helpers."""

from pathlib import Path

import studio_api.settings as settings


def test_settings_path_under_home(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "config_dir", lambda: tmp_path / ".screenflow")
    assert settings.settings_path() == tmp_path / ".screenflow" / "ui.json"


def test_migrate_legacy_then_load(tmp_path, monkeypatch):
    home_cfg = tmp_path / "home_cfg"
    legacy = tmp_path / "repo" / ".screenflow_ui.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text(
        '{"lang": "zh", "recent": [{"path": "E:/proj", "name": "P"}]}\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "config_dir", lambda: home_cfg)
    monkeypatch.setattr(settings, "legacy_settings_path", lambda: legacy)

    assert settings.migrate_legacy_settings_if_needed() is True
    dest = home_cfg / "ui.json"
    assert dest.is_file()
    data = settings.load_ui_settings()
    assert data["lang"] == "zh"
    assert data["recent"][0]["name"] == "P"
    # second call does not overwrite
    dest.write_text('{"lang": "en"}\n', encoding="utf-8")
    assert settings.migrate_legacy_settings_if_needed() is False
    assert settings.load_ui_settings()["lang"] == "en"


def test_touch_recent_writes_user_config(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "config_dir", lambda: tmp_path / ".screenflow")
    monkeypatch.setattr(
        settings, "legacy_settings_path", lambda: tmp_path / "missing.json"
    )
    proj = tmp_path / "myproj"
    proj.mkdir()
    settings.touch_recent(proj, "My Proj")
    recent = settings.get_recent()
    assert recent[0]["name"] == "My Proj"
    assert Path(recent[0]["path"]) == proj.resolve()


def test_resolve_reopen_prunes_stale(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "config_dir", lambda: tmp_path / ".screenflow")
    monkeypatch.setattr(
        settings, "legacy_settings_path", lambda: tmp_path / "missing.json"
    )
    good = tmp_path / "good"
    good.mkdir()
    (good / "project.json").write_text("{}", encoding="utf-8")
    bad = tmp_path / "gone"
    settings.update_ui_settings(
        reopen_last_project=True,
        recent=[
            {"path": str(bad), "name": "Gone"},
            {"path": str(good), "name": "Good"},
        ],
    )
    chosen = settings.resolve_reopen_project_path()
    assert chosen == good.resolve()
    names = [e["name"] for e in settings.get_recent()]
    assert "Gone" not in names
    assert "Good" in names


def test_reopen_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "config_dir", lambda: tmp_path / ".screenflow")
    monkeypatch.setattr(
        settings, "legacy_settings_path", lambda: tmp_path / "missing.json"
    )
    good = tmp_path / "good"
    good.mkdir()
    (good / "project.json").write_text("{}", encoding="utf-8")
    settings.update_ui_settings(
        reopen_last_project=False,
        recent=[{"path": str(good), "name": "Good"}],
    )
    assert settings.resolve_reopen_project_path() is None


def test_splitter_sizes_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "config_dir", lambda: tmp_path / ".screenflow")
    monkeypatch.setattr(
        settings, "legacy_settings_path", lambda: tmp_path / "missing.json"
    )
    settings.set_main_splitter_sizes([200, 600, 400])
    assert settings.get_main_splitter_sizes() == [200, 600, 400]
    # clamp tiny panes
    settings.set_main_splitter_sizes([10, 20, 30])
    assert settings.get_main_splitter_sizes() == [80, 80, 80]


def test_window_geometry_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "config_dir", lambda: tmp_path / ".screenflow")
    monkeypatch.setattr(
        settings, "legacy_settings_path", lambda: tmp_path / "missing.json"
    )
    settings.set_window_geometry("YWJjZA==")
    assert settings.get_window_geometry() == "YWJjZA=="


def test_runner_mode_settings(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "config_dir", lambda: tmp_path / ".screenflow")
    monkeypatch.setattr(
        settings, "legacy_settings_path", lambda: tmp_path / "missing.json"
    )
    monkeypatch.delenv("SCREENFLOW_RUNNER", raising=False)
    settings.set_runner_mode(settings.RUNNER_INLINE)
    assert settings.get_runner_mode() == settings.RUNNER_INLINE
    settings.set_runner_mode(settings.RUNNER_ELEVATE)
    assert settings.get_runner_mode() == settings.RUNNER_ELEVATE
    monkeypatch.setenv("SCREENFLOW_RUNNER", "inline")
    assert settings.get_runner_mode() == settings.RUNNER_INLINE



