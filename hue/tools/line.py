# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

import math

import cairo

from .base import ShapeTool, set_source


class LineTool(ShapeTool):
    id = "line"
    label = "Line"
    icon_name = "hue-line-symbolic"

    def render(self, cr, ctx, start, end):
        cr.set_line_width(ctx.size)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        set_source(cr, ctx.color)
        cr.move_to(*start)
        cr.line_to(*end)
        cr.stroke()

    def _constrain(self, point):
        """Snap the drag to the nearest 45° angle, keeping its length."""
        x, y = point
        sx, sy = self._start
        dx, dy = x - sx, y - sy
        angle = round(math.atan2(dy, dx) / (math.pi / 4)) * (math.pi / 4)
        length = math.hypot(dx, dy)
        return (sx + length * math.cos(angle), sy + length * math.sin(angle))
