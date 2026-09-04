# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

import cairo
from gi.repository import Gdk


@dataclass
class ToolContext:
    """Everything a tool needs for one interaction, handed over by the canvas."""

    surface: cairo.ImageSurface
    primary: Gdk.RGBA
    secondary: Gdk.RGBA
    button: int
    size: int
    fill_shapes: bool
    pick_color: Callable[[Gdk.RGBA, int], None]
    begin_text: Callable[[float, float, Gdk.RGBA], None]

    @property
    def color(self) -> Gdk.RGBA:
        return self.secondary if self.button == Gdk.BUTTON_SECONDARY else self.primary

    @property
    def alt_color(self) -> Gdk.RGBA:
        return self.primary if self.button == Gdk.BUTTON_SECONDARY else self.secondary


def set_source(cr: cairo.Context, color: Gdk.RGBA) -> None:
    cr.set_source_rgba(color.red, color.green, color.blue, color.alpha)


class Tool:
    id = ""
    label = ""
    icon_name = ""
    mutates = True

    def press(self, ctx: ToolContext, x: float, y: float) -> None:
        pass

    def motion(self, ctx: ToolContext, x: float, y: float) -> None:
        pass

    def release(self, ctx: ToolContext, x: float, y: float) -> None:
        pass

    def draw_preview(self, cr: cairo.Context, ctx: ToolContext) -> None:
        pass


class FreehandTool(Tool):
    """Draws a continuous stroke straight onto the document surface."""

    antialias = True
    line_cap = cairo.LINE_CAP_ROUND

    def __init__(self):
        self._last: tuple[float, float] | None = None

    def stroke_color(self, ctx: ToolContext) -> Gdk.RGBA:
        return ctx.color

    def _context(self, ctx: ToolContext) -> cairo.Context:
        cr = cairo.Context(ctx.surface)
        if not self.antialias:
            cr.set_antialias(cairo.ANTIALIAS_NONE)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_line_width(ctx.size)
        cr.set_line_cap(self.line_cap)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        set_source(cr, self.stroke_color(ctx))
        return cr

    def _snap(self, value: float) -> float:
        # Hard-edged tools need half-pixel offsets to land on whole pixels.
        return value if self.antialias else int(value) + 0.5

    def _dot(self, cr: cairo.Context, ctx: ToolContext, x: float, y: float) -> None:
        # Cairo renders nothing for a zero-length segment unless the cap is round,
        # so a click that never moves has to paint its own dot.
        radius = ctx.size / 2
        if self.line_cap == cairo.LINE_CAP_ROUND:
            cr.arc(x, y, radius, 0, 2 * math.pi)
        else:
            cr.rectangle(x - radius, y - radius, ctx.size, ctx.size)
        cr.fill()

    def press(self, ctx, x, y):
        x, y = self._snap(x), self._snap(y)
        self._last = (x, y)
        self._dot(self._context(ctx), ctx, x, y)

    def motion(self, ctx, x, y):
        if self._last is None:
            return
        x, y = self._snap(x), self._snap(y)
        cr = self._context(ctx)
        cr.move_to(*self._last)
        cr.line_to(x, y)
        cr.stroke()
        self._last = (x, y)

    def release(self, ctx, x, y):
        self.motion(ctx, x, y)
        self._last = None


class ShapeTool(Tool):
    """Rubber-bands a shape while dragging and commits it on release."""

    def __init__(self):
        self._start: tuple[float, float] | None = None
        self._current: tuple[float, float] | None = None

    def press(self, ctx, x, y):
        self._start = (x, y)
        self._current = (x, y)

    def motion(self, ctx, x, y):
        self._current = (x, y)

    def release(self, ctx, x, y):
        self._current = (x, y)
        if self._start is not None:
            cr = cairo.Context(ctx.surface)
            self.render(cr, ctx, self._start, self._current)
        self._start = None
        self._current = None

    def draw_preview(self, cr, ctx):
        if self._start is not None and self._current is not None:
            self.render(cr, ctx, self._start, self._current)

    def render(self, cr, ctx, start, end) -> None:
        raise NotImplementedError

    @staticmethod
    def rect(start, end) -> tuple[float, float, float, float]:
        x = min(start[0], end[0])
        y = min(start[1], end[1])
        return x, y, abs(end[0] - start[0]), abs(end[1] - start[1])

    def paint_shape(self, cr, ctx) -> None:
        """Fill with the alternate color when filling is on, then stroke the outline."""
        cr.set_line_width(ctx.size)
        cr.set_line_join(cairo.LINE_JOIN_MITER)
        if ctx.fill_shapes:
            set_source(cr, ctx.alt_color)
            cr.fill_preserve()
        set_source(cr, ctx.color)
        cr.stroke()
