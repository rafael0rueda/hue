# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

import math

from hue.tools.line import LineTool
from hue.tools.rectangle import RectangleTool


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
