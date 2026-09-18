# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import cairo

from ..i18n import _
from .base import Tool, set_source, snap_45

# A curve takes its line and then this many bends before it lands.
BENDS = 2


class CurveTool(Tool):
    """A line that is then bent, as in Paint.

    Drag out a straight line, then drag once to bend it towards the pointer and
    once more to bend it again. It lands after the second bend, or with Enter
    after the first.
    """

    id = "curve"
    label = _("Curve")
    icon_name = "tempera-curve-symbolic"
    fillable = False

    def __init__(self):
        self._start: tuple[float, float] | None = None
        self._end: tuple[float, float] | None = None
        self._controls: list[tuple[float, float]] = []
        self._bends = 0

    @property
    def in_progress(self) -> bool:
        return self._start is not None

    def press(self, ctx, x, y):
        if self._start is None:
            self._start = self._end = (x, y)
            return
        self._bends += 1
        self._bend_to((x, y))

    def _bend_to(self, point: tuple[float, float]) -> None:
        # The first bend pulls the whole curve one way; the second then pulls
        # its far half on its own, which is what makes an S shape possible.
        if self._bends == 1:
            self._controls = [point, point]
        else:
            self._controls[1] = point

    def motion(self, ctx, x, y):
        if self._start is None:
            return
        if self._bends == 0:
            self._end = snap_45(self._start, (x, y)) if ctx.constrain else (x, y)
        else:
            self._bend_to((x, y))

    def release(self, ctx, x, y):
        self.motion(ctx, x, y)
        if self._bends == 0 and self._start == self._end:
            # A click with no line to bend.
            self.cancel()
        elif self._bends >= BENDS:
            self.finish(ctx)

    def _path(self, cr: cairo.Context, ctx) -> None:
        cr.set_line_width(ctx.size)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        set_source(cr, ctx.color)
        cr.move_to(*self._start)
        if self._controls:
            cr.curve_to(*self._controls[0], *self._controls[1], *self._end)
        else:
            cr.line_to(*self._end)

    def draw_preview(self, cr, ctx):
        if self._start is None:
            return
        self._path(cr, ctx)
        cr.stroke()

    def finish(self, ctx):
        if self._start is not None:
            cr = cairo.Context(ctx.surface)
            self._path(cr, ctx)
            cr.stroke()
        self.cancel()

    def cancel(self):
        self._start = self._end = None
        self._controls = []
        self._bends = 0
