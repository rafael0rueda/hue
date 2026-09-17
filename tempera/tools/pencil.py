# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

import cairo

from .base import FreehandTool


class PencilTool(FreehandTool):
    id = "pencil"
    label = "Pencil"
    icon_name = "tempera-pencil-symbolic"
    antialias = False
    line_cap = cairo.LINE_CAP_SQUARE
