# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

from .base import Tool, ToolContext
from .brush import BrushTool
from .ellipse import EllipseTool
from .eraser import EraserTool
from .fill import FillTool
from .line import LineTool
from .pencil import PencilTool
from .picker import PickerTool
from .rectangle import RectangleTool
from .text import TextTool

TOOL_CLASSES = [
    PencilTool,
    BrushTool,
    EraserTool,
    LineTool,
    RectangleTool,
    EllipseTool,
    TextTool,
    FillTool,
    PickerTool,
]

SHAPE_TOOL_IDS = {LineTool.id, RectangleTool.id, EllipseTool.id}
TEXT_TOOL_ID = TextTool.id


def create_tools() -> dict[str, Tool]:
    return {cls.id: cls() for cls in TOOL_CLASSES}


__all__ = [
    "Tool",
    "ToolContext",
    "TOOL_CLASSES",
    "SHAPE_TOOL_IDS",
    "TEXT_TOOL_ID",
    "create_tools",
]
