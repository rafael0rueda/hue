# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from gi.repository import Adw, Gio, GLib, Gtk

from hue import recent_files, settings
from hue.window import HueWindow

from pixels import paint_pixel, pixel_at

RED = (1.0, 0.0, 0.0, 1.0)


@pytest.fixture(scope="module")
def application():
    app = Adw.Application(
        application_id="io.github.rafael0rueda.Hue.Tests",
        flags=Gio.ApplicationFlags.NON_UNIQUE,
    )
    # Windows can only be added once the application has started up.
    app.register(None)
    return app


@pytest.fixture
def window(application, monkeypatch, tmp_path):
    monkeypatch.setattr(recent_files, "_recent_file_path", lambda: tmp_path / "recent-files.txt")
    monkeypatch.setattr(settings, "_settings_path", lambda: tmp_path / "settings.ini")
    window = HueWindow(application)
    yield window
    window.destroy()


def test_undo_waits_while_a_stroke_is_under_way(window):
    document = window.canvas.document
    document.begin_change()
    paint_pixel(document.surface, 0, 0, RED)
    document.commit_change()

    window.canvas._drag_origin = (0.0, 0.0)
    window.activate_action("win.undo", None)
    assert pixel_at(window.canvas.document.surface, 0, 0) == (255, 0, 0, 255)

    window.canvas._drag_origin = None
    window.activate_action("win.undo", None)
    assert pixel_at(window.canvas.document.surface, 0, 0) == (255, 255, 255, 255)


def test_switching_tools_waits_while_a_stroke_is_under_way(window):
    window.canvas._drag_origin = (0.0, 0.0)
    window.lookup_action("tool").change_state(GLib.Variant.new_string("brush"))
    assert window.canvas.active_tool.id == "pencil"

    window.canvas._drag_origin = None
    window.lookup_action("tool").change_state(GLib.Variant.new_string("brush"))
    assert window.canvas.active_tool.id == "brush"


def test_zooming_still_works_while_a_stroke_is_under_way(window):
    window.canvas._drag_origin = (0.0, 0.0)
    window.activate_action("win.zoom-in", None)
    assert window.canvas.zoom > 1.0


def palette_position(window):
    return window.lookup_action("palette-position").get_state().get_string()


def test_palette_starts_at_the_bottom(window):
    assert palette_position(window) == "bottom"
    slot, _strip = window._palette_slots["bottom"]
    assert window._color_bar.get_parent() is slot
    assert window._color_bar.get_orientation() == Gtk.Orientation.HORIZONTAL


@pytest.mark.parametrize("position", ["left", "right"])
def test_palette_moves_to_a_side_strip(window, position):
    window.activate_action("win.palette-position", GLib.Variant.new_string(position))

    slot, strip = window._palette_slots[position]
    assert window._color_bar.get_parent() is slot
    assert window._color_bar.get_orientation() == Gtk.Orientation.VERTICAL
    visible = {name for name, (_slot, s) in window._palette_slots.items() if s and s.get_visible()}
    assert visible == {position}


def test_palette_returns_to_the_bottom(window):
    window.activate_action("win.palette-position", GLib.Variant.new_string("left"))
    window.activate_action("win.palette-position", GLib.Variant.new_string("bottom"))

    slot, _strip = window._palette_slots["bottom"]
    assert window._color_bar.get_parent() is slot
    assert window._color_bar.get_orientation() == Gtk.Orientation.HORIZONTAL
    assert not any(s.get_visible() for _slot, s in window._palette_slots.values() if s)


def test_unknown_palette_position_is_ignored(window):
    window.activate_action("win.palette-position", GLib.Variant.new_string("top"))
    assert palette_position(window) == "bottom"


def test_palette_position_is_remembered(application, window):
    window.activate_action("win.palette-position", GLib.Variant.new_string("right"))

    reopened = HueWindow(application)
    try:
        assert palette_position(reopened) == "right"
        slot, _strip = reopened._palette_slots["right"]
        assert reopened._color_bar.get_parent() is slot
    finally:
        reopened.destroy()


def test_tooltips_follow_changed_shortcuts(application, window):
    from hue import shortcuts

    swap = window._color_bar.swap_button
    assert swap.get_tooltip_text() == "Swap colors (X)"

    shortcuts.assign(application, "win.swap-colors", "<Shift>x")
    assert swap.get_tooltip_text() == "Swap colors (Shift+X)"

    shortcuts.assign(application, "win.swap-colors", None)
    assert swap.get_tooltip_text() == "Swap colors"

    shortcuts.reset(application)
    assert swap.get_tooltip_text() == "Swap colors (X)"


def test_bare_keys_pause_while_typing_including_new_ones(application, window):
    from hue import shortcuts

    shortcuts.assign(application, "win.crop", "c")
    window.canvas.begin_text(10, 10, window.colors.primary)
    try:
        assert application.get_accels_for_action("win.tool::pencil") == []
        assert application.get_accels_for_action("win.crop") == []
        assert application.get_accels_for_action("win.new") == ["<Control>n"]
    finally:
        window.canvas.cancel_text()
    assert application.get_accels_for_action("win.tool::pencil") == ["p"]
    assert application.get_accels_for_action("win.crop") == ["c"]
    shortcuts.reset(application)


def test_shortcuts_dialog_lists_every_shortcut(application, window):
    from hue import shortcuts
    from hue.shortcuts_dialog import ShortcutsDialog

    shortcuts.assign(application, "win.crop", "<Control>k")
    dialog = ShortcutsDialog(application)
    assert set(dialog._rows) == set(shortcuts.SHORTCUTS)
    keys, reset = dialog._rows["win.crop"]
    assert keys.get_accelerator() == "<Control>k"
    assert reset.get_visible()
    assert not dialog._rows["win.new"][1].get_visible()
    assert dialog._reset_all_row.get_sensitive()

    dialog._reset(shortcuts.SHORTCUTS["win.crop"])
    assert keys.get_accelerator() == ""
    assert not dialog._reset_all_row.get_sensitive()
