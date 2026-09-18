# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

from .base import Tool, ToolContext, draw_marquee
from .brush import BrushTool
from .eraser import EraserTool
from .fill import TOLERANCE as DEFAULT_TOLERANCE, FillTool
from .pencil import PencilTool
from .picker import PickerTool
from .select import SelectTool
from .shapes import DEFAULT_SHAPE, SHAPE_CLASSES, ShapesTool
from .text import TextTool

TOOL_CLASSES = [
    PencilTool,
    BrushTool,
    EraserTool,
    ShapesTool,
    TextTool,
    FillTool,
    PickerTool,
    SelectTool,
]

SHAPES_TOOL_ID = ShapesTool.id
SHAPE_IDS = [cls.id for cls in SHAPE_CLASSES]
ERASER_TOOL_ID = EraserTool.id
FILL_TOOL_ID = FillTool.id
TEXT_TOOL_ID = TextTool.id
SELECT_TOOL_ID = SelectTool.id


def create_tools() -> dict[str, Tool]:
    return {cls.id: cls() for cls in TOOL_CLASSES}


__all__ = [
    "Tool",
    "ToolContext",
    "draw_marquee",
    "TOOL_CLASSES",
    "SHAPE_CLASSES",
    "SHAPE_IDS",
    "DEFAULT_SHAPE",
    "SHAPES_TOOL_ID",
    "ERASER_TOOL_ID",
    "FILL_TOOL_ID",
    "DEFAULT_TOLERANCE",
    "TEXT_TOOL_ID",
    "SELECT_TOOL_ID",
    "create_tools",
]
