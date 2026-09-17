# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from gi.repository import Adw, Gio, GLib, Gtk

from tempera import recent_files, settings
from tempera.document import new_surface
from tempera.main import TemperaApplication
from tempera.window import TemperaWindow

from pixels import paint_pixel, pixel_at

RED = (1.0, 0.0, 0.0, 1.0)


@pytest.fixture(scope="module")
def application():
    app = Adw.Application(
        application_id="io.github.rafael0rueda.Tempera.Tests",
        flags=Gio.ApplicationFlags.NON_UNIQUE,
    )
    # Windows can only be added once the application has started up.
    app.register(None)
    return app


@pytest.fixture
def window(application, monkeypatch, tmp_path):
    monkeypatch.setattr(recent_files, "_recent_file_path", lambda: tmp_path / "recent-files.txt")
    monkeypatch.setattr(settings, "_settings_path", lambda: tmp_path / "settings.ini")
    window = TemperaWindow(application)
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


@pytest.mark.parametrize("position, columns", [("bottom", 10), ("left", 5), ("right", 2)])
def test_palette_grid_fits_where_it_is(window, position, columns):
    window.activate_action("win.palette-position", GLib.Variant.new_string(position))
    grid = window._color_bar._grid
    assert max(grid.query_child(child)[0] for child in window._color_bar._palette_swatches) == columns - 1


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

    reopened = TemperaWindow(application)
    try:
        assert palette_position(reopened) == "right"
        slot, _strip = reopened._palette_slots["right"]
        assert reopened._color_bar.get_parent() is slot
    finally:
        reopened.destroy()


def test_tooltips_follow_changed_shortcuts(application, window):
    from tempera import shortcuts

    swap = window._color_bar.swap_button
    assert swap.get_tooltip_text() == "Swap colors (X)"

    shortcuts.assign(application, "win.swap-colors", "<Shift>x")
    assert swap.get_tooltip_text() == "Swap colors (Shift+X)"

    shortcuts.assign(application, "win.swap-colors", None)
    assert swap.get_tooltip_text() == "Swap colors"

    shortcuts.reset(application)
    assert swap.get_tooltip_text() == "Swap colors (X)"


def test_bare_keys_pause_while_typing_including_new_ones(application, window):
    from tempera import shortcuts

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
    from tempera import shortcuts
    from tempera.shortcuts_dialog import ShortcutsDialog

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


def settle():
    context = GLib.MainContext.default()
    while context.pending():
        context.iteration(False)


def test_unchanged_window_closes_on_the_first_try(application, window):
    window.present()
    settle()
    window.close()
    settle()
    assert window not in application.get_windows()


def test_unsaved_changes_are_asked_about_before_closing(application, window):
    document = window.canvas.document
    document.begin_change()
    paint_pixel(document.surface, 0, 0, RED)
    document.commit_change()

    window.present()
    settle()
    window.close()
    settle()
    assert window in application.get_windows()
    assert isinstance(window.get_visible_dialog(), Adw.AlertDialog)


def test_scrolling_over_the_zoom_level_steps_the_zoom(window):
    window._on_zoom_label_scroll(None, 0, -1)
    zoomed_in = window.canvas.zoom
    assert zoomed_in > 1.0
    assert window._zoom_label.get_label() == f"{round(zoomed_in * 100)}%"

    window._on_zoom_label_scroll(None, 0, 1)
    window._on_zoom_label_scroll(None, 0, 1)
    assert window.canvas.zoom < 1.0


def test_a_floating_paste_is_asked_about_but_not_landed_on_close(application, window):
    window.canvas.begin_paste(new_surface(2, 2, RED), 0, 0)

    window.present()
    settle()
    window.close()
    settle()

    assert window in application.get_windows()
    assert isinstance(window.get_visible_dialog(), Adw.AlertDialog)
    # Cancel must leave things as they were, so nothing has landed yet.
    assert window.canvas.has_floating
    assert not window.canvas.document.can_undo


def test_an_empty_text_box_does_not_stop_the_window_closing(application, window):
    window.canvas.begin_text(10, 10, window.colors.primary)
    window.present()
    settle()
    window.close()
    settle()
    assert window not in application.get_windows()


def test_save_keeps_the_jpeg_quality_without_asking(window, tmp_path):
    path = tmp_path / "photo.jpg"
    window.canvas.document.file = Gio.File.new_for_path(str(path))
    window.present()
    settle()

    window.activate_action("win.save", None)
    settle()

    assert path.stat().st_size > 0
    assert window.get_visible_dialog() is None


def test_save_asks_where_for_an_image_it_cannot_write_back(window, tmp_path, monkeypatch):
    path = tmp_path / "animation.gif"
    path.write_bytes(b"the original animation")
    window.canvas.document.file = Gio.File.new_for_path(str(path))
    asked = []
    monkeypatch.setattr(window, "_save_as", lambda then=None: asked.append(then))

    window.activate_action("win.save", None)

    assert asked == [None]
    assert path.read_bytes() == b"the original animation"


def test_quit_closes_every_window_asking_about_unsaved_ones(application, window):
    changed = TemperaWindow(application)
    try:
        document = changed.canvas.document
        document.begin_change()
        paint_pixel(document.surface, 0, 0, RED)
        document.commit_change()
        window.present()
        changed.present()
        settle()

        TemperaApplication._on_quit(application)
        settle()

        assert window not in application.get_windows()
        assert changed in application.get_windows()
        assert isinstance(changed.get_visible_dialog(), Adw.AlertDialog)
    finally:
        changed.destroy()
