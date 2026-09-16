# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Gio

from hue import recent_files


def gio_file(path) -> Gio.File:
    return Gio.File.new_for_path(str(path))


def use_tmp_recent_file(monkeypatch, tmp_path):
    path = tmp_path / "recent-files.txt"
    monkeypatch.setattr(recent_files, "_recent_file_path", lambda: path)
    return path


def test_load_recent_is_empty_when_nothing_persisted(monkeypatch, tmp_path):
    use_tmp_recent_file(monkeypatch, tmp_path)
    assert recent_files.load_recent() == []


def test_remember_recent_adds_to_the_front(monkeypatch, tmp_path):
    use_tmp_recent_file(monkeypatch, tmp_path)
    recent_files.remember_recent(gio_file(tmp_path / "a.png"))
    recent_files.remember_recent(gio_file(tmp_path / "b.png"))
    recent = recent_files.load_recent()
    assert recent[0].endswith("b.png")
    assert recent[1].endswith("a.png")


def test_remember_recent_moves_an_existing_entry_to_the_front(monkeypatch, tmp_path):
    use_tmp_recent_file(monkeypatch, tmp_path)
    recent_files.remember_recent(gio_file(tmp_path / "a.png"))
    recent_files.remember_recent(gio_file(tmp_path / "b.png"))
    recent_files.remember_recent(gio_file(tmp_path / "a.png"))
    recent = recent_files.load_recent()
    assert recent[0].endswith("a.png")
    assert recent[1].endswith("b.png")
    assert len(recent) == 2


def test_remember_recent_caps_at_max_recent(monkeypatch, tmp_path):
    use_tmp_recent_file(monkeypatch, tmp_path)
    for i in range(recent_files.MAX_RECENT + 3):
        recent_files.remember_recent(gio_file(tmp_path / f"{i}.png"))
    recent = recent_files.load_recent()
    assert len(recent) == recent_files.MAX_RECENT
    # The most recently added files survive; the oldest are dropped.
    assert recent[0].endswith(f"{recent_files.MAX_RECENT + 2}.png")


def test_forget_recent_drops_one_entry_and_keeps_the_rest_in_order(monkeypatch, tmp_path):
    use_tmp_recent_file(monkeypatch, tmp_path)
    recent_files.remember_recent(gio_file(tmp_path / "a.png"))
    recent_files.remember_recent(gio_file(tmp_path / "b.png"))
    recent_files.remember_recent(gio_file(tmp_path / "c.png"))
    forgotten = gio_file(tmp_path / "b.png").get_uri()

    recent = recent_files.forget_recent(forgotten)

    assert recent == recent_files.load_recent()
    assert forgotten not in recent
    assert recent[0].endswith("c.png")
    assert recent[1].endswith("a.png")


def test_forget_recent_leaves_an_empty_file_when_the_last_entry_goes(monkeypatch, tmp_path):
    use_tmp_recent_file(monkeypatch, tmp_path)
    recent_files.remember_recent(gio_file(tmp_path / "a.png"))
    uri = gio_file(tmp_path / "a.png").get_uri()

    assert recent_files.forget_recent(uri) == []
    assert recent_files.load_recent() == []


def test_load_recent_is_empty_when_the_file_is_not_text(monkeypatch, tmp_path):
    path = use_tmp_recent_file(monkeypatch, tmp_path)
    path.write_bytes(b"\xff\xfe not utf-8")
    assert recent_files.load_recent() == []


def test_remember_recent_does_not_raise_when_the_list_cannot_be_written(monkeypatch, tmp_path):
    # A plain file where the config folder should be: nothing can be created in it.
    blocker = tmp_path / "hue"
    blocker.write_text("")
    monkeypatch.setattr(recent_files, "_recent_file_path", lambda: blocker / "recent-files.txt")

    recent = recent_files.remember_recent(gio_file(tmp_path / "a.png"))

    assert recent[0].endswith("a.png")
    assert recent_files.forget_recent(recent[0]) == []


def test_remember_recent_leaves_no_temporary_file_behind(monkeypatch, tmp_path):
    path = use_tmp_recent_file(monkeypatch, tmp_path)
    recent_files.remember_recent(gio_file(tmp_path / "a.png"))
    assert [child.name for child in tmp_path.iterdir()] == [path.name]
