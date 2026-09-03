from __future__ import annotations

import cairo
from gi.repository import Gdk, GObject, Gtk

from .color import ColorState
from .document import Document
from .tools import SHAPE_TOOL_IDS, Tool, ToolContext, create_tools

CHECKER_SIZE = 8


class Canvas(Gtk.DrawingArea):
    """Displays the document and routes pointer input to the active tool."""

    __gsignals__ = {
        "color-picked": (GObject.SignalFlags.RUN_FIRST, None, (Gdk.RGBA, int)),
    }

    def __init__(self, document: Document, colors: ColorState):
        super().__init__()
        self.colors = colors
        self.tools = create_tools()
        self.active_tool: Tool = self.tools["pencil"]
        self.brush_size = 4
        self.fill_shapes = False

        self._document: Document | None = None
        self._document_handler = 0
        self._drag_origin: tuple[float, float] | None = None
        self._drag_context: ToolContext | None = None

        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.CENTER)
        self.set_draw_func(self._draw)
        self.set_cursor(Gdk.Cursor.new_from_name("crosshair"))
        self.add_css_class("hue-canvas")

        drag = Gtk.GestureDrag(button=0)
        drag.connect("drag-begin", self._on_drag_begin)
        drag.connect("drag-update", self._on_drag_update)
        drag.connect("drag-end", self._on_drag_end)
        self.add_controller(drag)

        self.document = document

    @property
    def document(self) -> Document:
        return self._document

    @document.setter
    def document(self, value: Document) -> None:
        if self._document is not None and self._document_handler:
            self._document.disconnect(self._document_handler)
        self._document = value
        self._document_handler = value.connect("content-changed", lambda *_: self.queue_draw())
        self.set_content_width(value.width)
        self.set_content_height(value.height)
        self.queue_draw()

    def select_tool(self, tool_id: str) -> None:
        self.active_tool = self.tools[tool_id]

    @property
    def supports_fill(self) -> bool:
        return self.active_tool.id in SHAPE_TOOL_IDS

    def _make_context(self, button: int) -> ToolContext:
        return ToolContext(
            surface=self._document.surface,
            primary=self.colors.primary,
            secondary=self.colors.secondary,
            button=button,
            size=self.brush_size,
            fill_shapes=self.fill_shapes,
            pick_color=lambda color, btn: self.emit("color-picked", color, btn),
        )

    def _on_drag_begin(self, gesture, start_x, start_y):
        button = gesture.get_current_button()
        self._drag_origin = (start_x, start_y)
        self._drag_context = self._make_context(button)

        if self.active_tool.mutates:
            self._document.begin_change()
        self.active_tool.press(self._drag_context, start_x, start_y)
        self.queue_draw()

    def _on_drag_update(self, gesture, offset_x, offset_y):
        if self._drag_origin is None:
            return
        x, y = self._drag_origin[0] + offset_x, self._drag_origin[1] + offset_y
        self.active_tool.motion(self._drag_context, x, y)
        self.queue_draw()

    def _on_drag_end(self, gesture, offset_x, offset_y):
        if self._drag_origin is None:
            return
        x, y = self._drag_origin[0] + offset_x, self._drag_origin[1] + offset_y
        self.active_tool.release(self._drag_context, x, y)

        if self.active_tool.mutates:
            self._document.commit_change()
        self._drag_origin = None
        self._drag_context = None
        self.queue_draw()

    def _draw(self, area, cr: cairo.Context, width: int, height: int, *_):
        self._draw_checkerboard(cr, width, height)

        cr.set_source_surface(self._document.surface, 0, 0)
        cr.paint()

        if self._drag_context is not None:
            cr.save()
            self.active_tool.draw_preview(cr, self._drag_context)
            cr.restore()

        outline = self.get_color()
        cr.set_source_rgba(outline.red, outline.green, outline.blue, 0.25)
        cr.set_line_width(1)
        cr.rectangle(0.5, 0.5, width - 1, height - 1)
        cr.stroke()

    @staticmethod
    def _draw_checkerboard(cr: cairo.Context, width: int, height: int) -> None:
        cr.set_source_rgb(1, 1, 1)
        cr.paint()
        cr.set_source_rgb(0.9, 0.9, 0.9)
        for row in range(0, height, CHECKER_SIZE):
            for column in range(0, width, CHECKER_SIZE):
                if (row // CHECKER_SIZE + column // CHECKER_SIZE) % 2:
                    cr.rectangle(column, row, CHECKER_SIZE, CHECKER_SIZE)
        cr.fill()
