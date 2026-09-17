# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

from hue import settings


def use_tmp_settings_file(monkeypatch, tmp_path):
    path = tmp_path / "hue" / "settings.ini"
    monkeypatch.setattr(settings, "_settings_path", lambda: path)
    return path


def test_palette_defaults_to_the_bottom(monkeypatch, tmp_path):
    use_tmp_settings_file(monkeypatch, tmp_path)
    assert settings.load_palette_position() == "bottom"


def test_palette_position_round_trips(monkeypatch, tmp_path):
    use_tmp_settings_file(monkeypatch, tmp_path)
    settings.save_palette_position("left")
    assert settings.load_palette_position() == "left"


def test_unknown_palette_position_falls_back_to_the_default(monkeypatch, tmp_path):
    path = use_tmp_settings_file(monkeypatch, tmp_path)
    path.parent.mkdir()
    path.write_text("[view]\npalette-position = top\n", encoding="utf-8")
    assert settings.load_palette_position() == "bottom"


def test_damaged_settings_file_falls_back_to_the_default(monkeypatch, tmp_path):
    path = use_tmp_settings_file(monkeypatch, tmp_path)
    path.parent.mkdir()
    path.write_text("not an ini file", encoding="utf-8")
    assert settings.load_palette_position() == "bottom"
    settings.save_palette_position("right")
    assert settings.load_palette_position() == "right"


def test_unwritable_config_directory_is_not_an_error(monkeypatch, tmp_path):
    blocker = tmp_path / "hue"
    blocker.write_text("a file where the directory should be", encoding="utf-8")
    use_tmp_settings_file(monkeypatch, tmp_path)
    settings.save_palette_position("left")
    assert settings.load_palette_position() == "bottom"
