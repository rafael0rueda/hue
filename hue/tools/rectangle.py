from .base import ShapeTool


class RectangleTool(ShapeTool):
    id = "rectangle"
    label = "Rectangle"
    icon_name = "hue-rectangle-symbolic"

    def render(self, cr, ctx, start, end):
        cr.rectangle(*self.rect(start, end))
        self.paint_shape(cr, ctx)
