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
    select_region: Callable[[float, float, float, float], None]
    # Shift held: squares up a shape or snaps a line to a 45° angle.
    constrain: bool = False
    # The eraser rubs back to transparency rather than to the secondary color.
    erase_to_transparency: bool = False
    # How far from the color under the pointer a flood fill still spreads.
    tolerance: int = 32
    # How close, in image pixels, a click must land to hit a point already
    # placed, such as the first corner of a polygon being closed.
    reach: float = 4.0

    @property
    def color(self) -> Gdk.RGBA:
        return self.secondary if self.button == Gdk.BUTTON_SECONDARY else self.primary

    @property
    def alt_color(self) -> Gdk.RGBA:
        return self.primary if self.button == Gdk.BUTTON_SECONDARY else self.secondary


def set_source(cr: cairo.Context, color: Gdk.RGBA) -> None:
    cr.set_source_rgba(color.red, color.green, color.blue, color.alpha)


def draw_marquee(cr: cairo.Context, x: float, y: float, width: float, height: float) -> None:
    """The dashed outline of a selection: black over white, so it reads on any artwork."""
    cr.save()
    cr.set_line_width(1)
    cr.rectangle(x + 0.5, y + 0.5, max(width - 1, 0), max(height - 1, 0))
    cr.set_source_rgb(1, 1, 1)
    cr.stroke_preserve()
    cr.set_dash([4, 4])
    cr.set_source_rgb(0, 0, 0)
    cr.stroke()
    cr.restore()


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

    # Tools that take several clicks, such as the polygon, stay in progress
    # between drags. The canvas keeps drawing their preview, sends them the
    # pointer as it hovers, and lets Enter finish them or Esc drop them.

    @property
    def in_progress(self) -> bool:
        return False

    def hover(self, x: float, y: float) -> None:
        pass

    def finish(self, ctx: ToolContext) -> None:
        """Draw what has been placed so far into the image."""

    def cancel(self) -> None:
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
        # A see-through color paints over what is there; an opaque one replaces
        # it, which is what lets the eraser rub back to transparency.
        color = self.stroke_color(ctx)
        cr.set_operator(
            cairo.OPERATOR_OVER if 0 < color.alpha < 1 else cairo.OPERATOR_SOURCE
        )
        cr.set_line_width(ctx.size)
        cr.set_line_cap(self.line_cap)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        set_source(cr, color)
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


def snap_45(origin: tuple[float, float], point: tuple[float, float]) -> tuple[float, float]:
    """Turn the line from origin to point to the nearest 45° angle, keeping its length."""
    x, y = point
    sx, sy = origin
    dx, dy = x - sx, y - sy
    angle = round(math.atan2(dy, dx) / (math.pi / 4)) * (math.pi / 4)
    length = math.hypot(dx, dy)
    return (sx + length * math.cos(angle), sy + length * math.sin(angle))


class ShapeTool(Tool):
    """Rubber-bands a shape while dragging and commits it on release."""

    # Whether "Fill shape" applies: closed shapes have an inside to fill.
    fillable = True

    def __init__(self):
        self._start: tuple[float, float] | None = None
        self._current: tuple[float, float] | None = None

    def press(self, ctx, x, y):
        self._start = (x, y)
        self._current = (x, y)

    def motion(self, ctx, x, y):
        self._current = self._constrain((x, y)) if ctx.constrain else (x, y)

    def release(self, ctx, x, y):
        self._current = self._constrain((x, y)) if ctx.constrain else (x, y)
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

    def _constrain(self, point: tuple[float, float]) -> tuple[float, float]:
        """Square up the drag: equal width and height, same direction as the drag."""
        x, y = point
        sx, sy = self._start
        size = max(abs(x - sx), abs(y - sy))
        return (sx + size * (1 if x >= sx else -1), sy + size * (1 if y >= sy else -1))

    @staticmethod
    def rect(start, end) -> tuple[float, float, float, float]:
        x = min(start[0], end[0])
        y = min(start[1], end[1])
        return x, y, abs(end[0] - start[0]), abs(end[1] - start[1])

    def paint_shape(self, cr, ctx) -> None:
        paint_shape(cr, ctx)


def paint_shape(cr: cairo.Context, ctx: ToolContext) -> None:
    """Fill the path with the alternate color when filling is on, then stroke its outline."""
    cr.set_line_width(ctx.size)
    cr.set_line_join(cairo.LINE_JOIN_MITER)
    if ctx.fill_shapes:
        set_source(cr, ctx.alt_color)
        cr.fill_preserve()
    set_source(cr, ctx.color)
    cr.stroke()
