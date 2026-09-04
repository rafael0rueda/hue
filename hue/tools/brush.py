# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

from .base import FreehandTool


class BrushTool(FreehandTool):
    id = "brush"
    label = "Brush"
    icon_name = "hue-brush-symbolic"
