# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from gi.repository import Adw, Gio, GLib

from hue import recent_files
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
