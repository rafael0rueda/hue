from .base import Tool, ToolContext
from .brush import BrushTool
from .ellipse import EllipseTool
from .eraser import EraserTool
from .fill import FillTool
from .line import LineTool
from .pencil import PencilTool
from .picker import PickerTool
from .rectangle import RectangleTool

TOOL_CLASSES = [
    PencilTool,
    BrushTool,
    EraserTool,
    LineTool,
    RectangleTool,
    EllipseTool,
    FillTool,
    PickerTool,
]

SHAPE_TOOL_IDS = {LineTool.id, RectangleTool.id, EllipseTool.id}


def create_tools() -> dict[str, Tool]:
    return {cls.id: cls() for cls in TOOL_CLASSES}


__all__ = ["Tool", "ToolContext", "TOOL_CLASSES", "SHAPE_TOOL_IDS", "create_tools"]
