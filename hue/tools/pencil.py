from .base import FreehandTool
import cairo


class PencilTool(FreehandTool):
    id = "pencil"
    label = "Pencil"
    icon_name = "hue-pencil-symbolic"
    antialias = False
    line_cap = cairo.LINE_CAP_SQUARE
