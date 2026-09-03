import math

from .base import ShapeTool


class EllipseTool(ShapeTool):
    id = "ellipse"
    label = "Ellipse"
    icon_name = "hue-ellipse-symbolic"

    def render(self, cr, ctx, start, end):
        x, y, width, height = self.rect(start, end)
        if width <= 0 or height <= 0:
            return
        cr.save()
        cr.translate(x + width / 2, y + height / 2)
        cr.scale(width / 2, height / 2)
        cr.arc(0, 0, 1, 0, 2 * math.pi)
        cr.restore()
        self.paint_shape(cr, ctx)
