# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

import cairo

from .base import FreehandTool, ToolContext


class EraserTool(FreehandTool):
    id = "eraser"
    label = "Eraser"
    icon_name = "hue-eraser-symbolic"
    antialias = False
    line_cap = cairo.LINE_CAP_SQUARE

    def stroke_color(self, ctx: ToolContext):
        # Like Paint, the eraser lays down the background (secondary) color.
        return ctx.secondary
