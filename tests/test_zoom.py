# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

from hue.canvas import ZOOM_MAX, ZOOM_MIN, ZOOM_PRESETS, Canvas
from hue.color import ColorState
from hue.document import Document


def make_canvas() -> Canvas:
    return Canvas(Document(), ColorState())


def test_default_zoom_is_100_percent():
    assert make_canvas().zoom == 1.0


def test_zoom_in_and_out_step_through_presets():
    canvas = make_canvas()
    canvas.zoom_in()
    assert canvas.zoom == ZOOM_PRESETS[ZOOM_PRESETS.index(1.0) + 1]

    canvas.zoom_out()
    assert canvas.zoom == 1.0

    canvas.zoom_out()
    assert canvas.zoom == ZOOM_PRESETS[ZOOM_PRESETS.index(1.0) - 1]


def test_zoom_in_past_the_top_preset_clamps_to_zoom_max():
    canvas = make_canvas()
    canvas.set_zoom(ZOOM_MAX)
    canvas.zoom_in()
    assert canvas.zoom == ZOOM_MAX


def test_zoom_out_past_the_bottom_preset_clamps_to_zoom_min():
    canvas = make_canvas()
    canvas.set_zoom(ZOOM_MIN)
    canvas.zoom_out()
    assert canvas.zoom == ZOOM_MIN


def test_set_zoom_clamps_to_the_allowed_range():
    canvas = make_canvas()
    canvas.set_zoom(ZOOM_MAX * 10)
    assert canvas.zoom == ZOOM_MAX

    canvas.set_zoom(ZOOM_MIN / 10)
    assert canvas.zoom == ZOOM_MIN


def test_reset_zoom_returns_to_100_percent():
    canvas = make_canvas()
    canvas.set_zoom(2.0)
    canvas.reset_zoom()
    assert canvas.zoom == 1.0


def test_set_zoom_to_the_current_value_is_a_no_op():
    canvas = make_canvas()
    changes = []
    canvas.connect("zoom-changed", lambda _canvas, zoom: changes.append(zoom))
    canvas.set_zoom(1.0)
    assert changes == []


def test_set_zoom_emits_zoom_changed():
    canvas = make_canvas()
    changes = []
    canvas.connect("zoom-changed", lambda _canvas, zoom: changes.append(zoom))
    canvas.set_zoom(2.0)
    assert changes == [2.0]
