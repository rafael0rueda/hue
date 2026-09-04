# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

from .base import FreehandTool
import cairo


class PencilTool(FreehandTool):
    id = "pencil"
    label = "Pencil"
    icon_name = "hue-pencil-symbolic"
    antialias = False
    line_cap = cairo.LINE_CAP_SQUARE
