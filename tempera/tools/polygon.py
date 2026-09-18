# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import math

import cairo

from ..i18n import _
from .base import Tool, paint_shape, set_source, snap_45


class PolygonTool(Tool):
    """A shape of straight sides, placed one corner at a time.

    Drag out the first side, or click its first corner, then click each corner
    after it. Clicking the first corner again closes the shape; so does clicking
    the last corner twice, or pressing Enter.
    """

    id = "polygon"
    label = _("Polygon")
    icon_name = "tempera-polygon-symbolic"
    fillable = True

    def __init__(self):
        self._points: list[tuple[float, float]] = []
        # Where the pointer hovers between clicks, for the side still to come.
        self._hover: tuple[float, float] | None = None
        # The press landed on a corner already placed, so its release closes the shape.
        self._closing = False
        self._dragging = False

    @property
    def in_progress(self) -> bool:
        return bool(self._points)

    @property
    def points(self) -> list[tuple[float, float]]:
        return list(self._points)

    @staticmethod
    def _near(a: tuple[float, float], b: tuple[float, float], reach: float) -> bool:
        return math.hypot(a[0] - b[0], a[1] - b[1]) <= reach

    def press(self, ctx, x, y):
        self._hover = None
        self._dragging = True
        if not self._points:
            # The first corner, and the second following the drag from it.
            self._points = [(x, y), (x, y)]
            return
        closes_at_start = len(self._points) >= 3 and self._near((x, y), self._points[0], ctx.reach)
        if closes_at_start or self._near((x, y), self._points[-1], ctx.reach):
            self._closing = True
            return
        self._points.append((x, y))

    def motion(self, ctx, x, y):
        if self._closing or len(self._points) < 2:
            return
        point = (x, y)
        if ctx.constrain:
            point = snap_45(self._points[-2], point)
        self._points[-1] = point

    def release(self, ctx, x, y):
        self.motion(ctx, x, y)
        self._dragging = False
        if self._closing:
            self.finish(ctx)
            return
        if len(self._points) == 2 and self._near(self._points[0], self._points[1], ctx.reach):
            # A click rather than a drag: only the first corner is placed.
            self._points.pop()

    def hover(self, x, y):
        self._hover = (x, y)

    def draw_preview(self, cr, ctx):
        if not self._points:
            return
        points = list(self._points)
        if self._hover is not None and not self._dragging:
            points.append(self._hover)
        cr.set_line_width(ctx.size)
        cr.set_line_join(cairo.LINE_JOIN_MITER)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        set_source(cr, ctx.color)
        cr.move_to(*points[0])
        for point in points[1:]:
            cr.line_to(*point)
        if len(points) == 1:
            # Cairo draws a round-capped dot for a path that goes nowhere.
            cr.close_path()
        cr.stroke()

    def finish(self, ctx):
        points = self._points
        self.cancel()
        if len(points) < 2:
            return
        cr = cairo.Context(ctx.surface)
        cr.move_to(*points[0])
        for point in points[1:]:
            cr.line_to(*point)
        if len(points) == 2:
            # Two corners make only a side, which has no inside to fill.
            cr.set_line_width(ctx.size)
            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            set_source(cr, ctx.color)
            cr.stroke()
            return
        cr.close_path()
        paint_shape(cr, ctx)

    def cancel(self):
        self._points = []
        self._hover = None
        self._closing = False
        self._dragging = False
