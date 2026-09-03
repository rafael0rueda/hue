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
