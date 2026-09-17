# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

import math

from gi.repository import Gdk

from tempera.document import new_surface
from tempera.tools.base import ToolContext
from tempera.tools.brush import BrushTool
from tempera.tools.eraser import EraserTool
from tempera.tools.line import LineTool
from tempera.tools.rectangle import RectangleTool

from pixels import pixel_at

RED = (1.0, 0.0, 0.0, 1.0)


def rgba(spec: str) -> Gdk.RGBA:
    color = Gdk.RGBA()
    color.parse(spec)
    return color


def context(surface, button: int, primary: Gdk.RGBA | None = None, size: int = 1) -> ToolContext:
    """A tool context with nothing but the pixels and the colours filled in."""
    return ToolContext(
        surface=surface,
        primary=primary or rgba("#000000"),
        secondary=rgba("#ffffff"),
        button=button,
        size=size,
        fill_shapes=False,
        pick_color=lambda color, btn: None,
        begin_text=lambda x, y, color: None,
        select_region=lambda x, y, width, height: None,
    )


# ShapeTool._constrain (square), exercised through RectangleTool


def test_constrain_squares_up_a_wide_drag():
    tool = RectangleTool()
    tool._start = (0, 0)
    assert tool._constrain((10, 3)) == (10, 10)


def test_constrain_squares_up_a_tall_drag():
    tool = RectangleTool()
    tool._start = (0, 0)
    assert tool._constrain((3, 10)) == (10, 10)


def test_constrain_keeps_the_drags_direction():
    tool = RectangleTool()
    tool._start = (0, 0)
    assert tool._constrain((-10, -3)) == (-10, -10)
    assert tool._constrain((4, -9)) == (9, -9)


def test_motion_only_constrains_when_the_context_asks_for_it():
    tool = RectangleTool()
    tool._start = (0, 0)

    class Ctx:
        constrain = False

    tool.motion(Ctx(), 10, 3)
    assert tool._current == (10, 3)

    Ctx.constrain = True
    tool.motion(Ctx(), 10, 3)
    assert tool._current == (10, 10)


# LineTool._constrain (45° snap)


def test_line_constrain_snaps_a_near_horizontal_drag():
    tool = LineTool()
    tool._start = (0, 0)
    x, y = tool._constrain((10, 1))
    assert x == math.hypot(10, 1)
    assert y == 0


def test_line_constrain_snaps_a_45_degree_drag_almost_exactly():
    tool = LineTool()
    tool._start = (0, 0)
    x, y = tool._constrain((10, 9))
    length = math.hypot(10, 9)
    assert math.isclose(x, y)
    assert math.isclose(math.hypot(x, y), length)


def test_line_constrain_snaps_a_near_vertical_drag():
    tool = LineTool()
    tool._start = (0, 0)
    x, y = tool._constrain((1, 10))
    assert math.isclose(x, 0, abs_tol=1e-9)
    assert y == math.hypot(1, 10)


def test_line_constrain_snaps_a_135_degree_drag():
    tool = LineTool()
    tool._start = (0, 0)
    x, y = tool._constrain((-9, 10))
    assert math.isclose(-x, y)


# the eraser


def test_the_eraser_lays_down_the_secondary_color():
    surface = new_surface(4, 4, RED)
    ctx = context(surface, button=Gdk.BUTTON_PRIMARY)
    EraserTool().press(ctx, 1, 1)
    assert pixel_at(surface, 1, 1) == (255, 255, 255, 255)


def test_the_eraser_can_rub_back_to_transparency():
    surface = new_surface(4, 4, RED)
    ctx = context(surface, button=Gdk.BUTTON_PRIMARY)
    ctx.erase_to_transparency = True
    EraserTool().press(ctx, 1, 1)
    assert pixel_at(surface, 1, 1) == (0, 0, 0, 0)


def test_a_see_through_color_paints_over_what_is_there():
    """An opaque stroke replaces the pixels; a see-through one blends with them."""
    surface = new_surface(8, 8, RED)
    half_white = Gdk.RGBA()
    half_white.parse("rgba(255,255,255,0.5)")
    ctx = context(surface, button=Gdk.BUTTON_PRIMARY, primary=half_white, size=6)
    BrushTool().press(ctx, 4, 4)
    red, green, blue, alpha = pixel_at(surface, 4, 4)
    assert alpha == 255
    assert red == 255 and 100 < green < 200
