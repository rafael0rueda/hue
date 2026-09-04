# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass

import cairo
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk

from .clipboard import surface_from_file, surface_from_texture
from .color import ColorState
from .document import MAX_SIZE, Document
from .tools import SHAPE_TOOL_IDS, Tool, ToolContext, create_tools

CHECKER_SIZE = 8
HANDLE_SIZE = 10
HANDLE_GRAB = 12
# Room around the image so the grips sitting on its edge are fully visible.
HANDLE_MARGIN = 8

HANDLE_CURSORS = {"e": "ew-resize", "s": "ns-resize", "se": "nwse-resize", "paste": "move"}


@dataclass
class FloatingPaste:
    """Pasted pixels hovering over the canvas until they are stamped down."""

    surface: cairo.ImageSurface
    x: float = 0.0
    y: float = 0.0

    @property
    def width(self) -> int:
        return self.surface.get_width()

    @property
    def height(self) -> int:
        return self.surface.get_height()

    def move_to(self, x: float, y: float) -> None:
        # Never past the top-left: the canvas only ever grows right and down, so
        # the image keeps the same anchor a resize would give it.
        self.x = max(0.0, x)
        self.y = max(0.0, y)

    def contains(self, x: float, y: float) -> bool:
        return self.x <= x <= self.x + self.width and self.y <= y <= self.y + self.height


class Canvas(Gtk.DrawingArea):
    """Displays the document and routes pointer input to the active tool."""

    __gsignals__ = {
        "color-picked": (GObject.SignalFlags.RUN_FIRST, None, (Gdk.RGBA, int)),
        "resize-preview": (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
        "paste-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
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
        self._resize_handle: str | None = None
        self._resize_size: tuple[int, int] | None = None
        self._paste: FloatingPaste | None = None
        self._paste_origin: tuple[float, float] | None = None

        # Anchored top-left like the image itself, so dragging a resize grip does
        # not move the widget out from under the pointer.
        self.set_halign(Gtk.Align.START)
        self.set_valign(Gtk.Align.START)
        self.set_draw_func(self._draw)
        self.set_cursor(Gdk.Cursor.new_from_name("crosshair"))
        self.add_css_class("hue-canvas")

        drag = Gtk.GestureDrag(button=0)
        drag.connect("drag-begin", self._on_drag_begin)
        drag.connect("drag-update", self._on_drag_update)
        drag.connect("drag-end", self._on_drag_end)
        self.add_controller(drag)

        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self._on_motion)
        motion.connect("leave", lambda *_: self._set_cursor(None))
        self.add_controller(motion)

        # Enter and Escape only mean something while a paste is floating, so the
        # canvas takes focus for the duration rather than claiming accelerators.
        self.set_focusable(True)
        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._on_key_pressed)
        self.add_controller(keys)

        drop = Gtk.DropTarget.new(Gdk.Texture, Gdk.DragAction.COPY)
        drop.set_gtypes([Gdk.Texture, Gdk.FileList, Gio.File])
        drop.connect("drop", self._on_drop)
        self.add_controller(drop)

        self.document = document

    @property
    def document(self) -> Document:
        return self._document

    @document.setter
    def document(self, value: Document) -> None:
        if self._document is not None and self._document_handler:
            self._document.disconnect(self._document_handler)
        self._document = value
        self._document_handler = value.connect("content-changed", self._on_content_changed)
        self._sync_content_size()
        self.queue_draw()

    def _on_content_changed(self, *_) -> None:
        # Undo/redo and resizing can swap in a differently sized surface.
        self._sync_content_size()
        self.queue_draw()

    def _sync_content_size(self) -> None:
        width, height = self._document.width, self._document.height
        if self._resize_size is not None:
            # Follow the drag so the pending outline stays inside the widget.
            width = max(width, self._resize_size[0])
            height = max(height, self._resize_size[1])
        if self._paste is not None:
            # A screenshot hanging off the edge stays visible before it lands.
            width = max(width, round(self._paste.x) + self._paste.width)
            height = max(height, round(self._paste.y) + self._paste.height)
        self.set_content_width(width + HANDLE_MARGIN)
        self.set_content_height(height + HANDLE_MARGIN)

    def select_tool(self, tool_id: str) -> None:
        self.active_tool = self.tools[tool_id]

    @property
    def supports_fill(self) -> bool:
        return self.active_tool.id in SHAPE_TOOL_IDS

    # Floating paste

    @property
    def has_paste(self) -> bool:
        return self._paste is not None

    @property
    def pending_size(self) -> tuple[int, int]:
        """The canvas size a commit would leave behind, for the size readout."""
        width, height = self._document.width, self._document.height
        if self._paste is None:
            return width, height
        return (
            min(max(width, round(self._paste.x) + self._paste.width), MAX_SIZE),
            min(max(height, round(self._paste.y) + self._paste.height), MAX_SIZE),
        )

    def begin_paste(self, surface: cairo.ImageSurface, x: float = 0, y: float = 0) -> None:
        """Float an image over the canvas until it is committed or discarded."""
        self.commit_paste()
        self._paste = FloatingPaste(surface)
        self._paste.move_to(x, y)
        self.grab_focus()
        self._sync_content_size()
        self.queue_draw()
        self.emit("paste-changed")

    def commit_paste(self) -> bool:
        """Stamp the floating image into the document, growing the canvas to fit."""
        if self._paste is None:
            return False
        paste, self._paste = self._paste, None
        self._document.paste(paste.surface, round(paste.x), round(paste.y))
        self._sync_content_size()
        self.queue_draw()
        self.emit("paste-changed")
        return True

    def cancel_paste(self) -> bool:
        if self._paste is None:
            return False
        self._paste = None
        self._sync_content_size()
        self.queue_draw()
        self.emit("paste-changed")
        return True

    def _on_key_pressed(self, controller, keyval, keycode, state) -> bool:
        if self._paste is None:
            return False
        if keyval == Gdk.KEY_Escape:
            return self.cancel_paste()
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            return self.commit_paste()
        return False

    def _on_drop(self, target, value, x: float, y: float) -> bool:
        if isinstance(value, Gdk.FileList):
            files = value.get_files()
            value = files[0] if files else None
        try:
            if isinstance(value, Gdk.Texture):
                surface = surface_from_texture(value)
            elif isinstance(value, Gio.File):
                surface = surface_from_file(value)
            else:
                return False
        except (GLib.Error, TypeError):
            # An unreadable file or a format GdkPixbuf does not know.
            return False
        # Drop where the pointer let go, centred on the pasted image.
        self.begin_paste(surface, x - surface.get_width() / 2, y - surface.get_height() / 2)
        return True

    # Resize grips

    def _handles(self) -> dict[str, tuple[float, float]]:
        if self._paste is not None:
            # The paste owns the pointer until it lands.
            return {}
        width, height = self._resize_size or (self._document.width, self._document.height)
        return {
            "e": (width, height / 2),
            "s": (width / 2, height),
            "se": (width, height),
        }

    def _handle_at(self, x: float, y: float) -> str | None:
        for name, (hx, hy) in self._handles().items():
            if abs(x - hx) <= HANDLE_GRAB and abs(y - hy) <= HANDLE_GRAB:
                return name
        return None

    def _set_cursor(self, handle: str | None) -> None:
        name = HANDLE_CURSORS.get(handle, "crosshair")
        self.set_cursor(Gdk.Cursor.new_from_name(name))

    def _on_motion(self, controller, x, y) -> None:
        if self._drag_origin is not None:
            return
        if self._paste is not None and self._paste.contains(x, y):
            self._set_cursor("paste")
            return
        self._set_cursor(self._handle_at(x, y))

    def _resized_to(self, x: float, y: float) -> tuple[int, int]:
        width, height = self._document.width, self._document.height
        if self._resize_handle in ("e", "se"):
            width = round(x)
        if self._resize_handle in ("s", "se"):
            height = round(y)
        return max(1, min(width, MAX_SIZE)), max(1, min(height, MAX_SIZE))

    # Pointer input

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
        self._drag_origin = (start_x, start_y)

        if self._paste is not None:
            if self._paste.contains(start_x, start_y):
                self._paste_origin = (self._paste.x, self._paste.y)
                self._set_cursor("paste")
            else:
                # Clicking away lands the paste; the click itself does not draw.
                self.commit_paste()
            return

        handle = self._handle_at(start_x, start_y)
        if handle is not None:
            self._resize_handle = handle
            self._resize_size = (self._document.width, self._document.height)
            self._set_cursor(handle)
            self.queue_draw()
            return

        self._drag_context = self._make_context(gesture.get_current_button())
        if self.active_tool.mutates:
            self._document.begin_change()
        self.active_tool.press(self._drag_context, start_x, start_y)
        self.queue_draw()

    def _on_drag_update(self, gesture, offset_x, offset_y):
        if self._drag_origin is None:
            return
        x, y = self._drag_origin[0] + offset_x, self._drag_origin[1] + offset_y

        if self._paste_origin is not None:
            self._paste.move_to(self._paste_origin[0] + offset_x, self._paste_origin[1] + offset_y)
            self._sync_content_size()
            self.queue_draw()
            self.emit("paste-changed")
            return

        if self._resize_handle is not None:
            self._resize_size = self._resized_to(x, y)
            self._sync_content_size()
            self.emit("resize-preview", *self._resize_size)
            self.queue_draw()
            return

        if self._drag_context is None:
            return

        self.active_tool.motion(self._drag_context, x, y)
        self.queue_draw()

    def _on_drag_end(self, gesture, offset_x, offset_y):
        if self._drag_origin is None:
            return
        x, y = self._drag_origin[0] + offset_x, self._drag_origin[1] + offset_y

        if self._paste_origin is not None or self._paste is not None:
            # A floating paste stays floating; the drag only moved it.
            self._paste_origin = None
            self._drag_origin = None
            return

        if self._resize_handle is not None:
            width, height = self._resized_to(x, y)
            self._resize_handle = None
            self._resize_size = None
            self._drag_origin = None
            self._document.resize(width, height)
            self._sync_content_size()
            self.queue_draw()
            return

        if self._drag_context is None:
            # The press landed a paste instead of starting a stroke.
            self._drag_origin = None
            return

        self.active_tool.release(self._drag_context, x, y)
        if self.active_tool.mutates:
            self._document.commit_change()
        self._drag_origin = None
        self._drag_context = None
        self.queue_draw()

    # Drawing

    def _draw(self, area, cr: cairo.Context, width: int, height: int, *_):
        image_width, image_height = self._document.width, self._document.height

        cr.save()
        cr.rectangle(0, 0, image_width, image_height)
        cr.clip()
        self._draw_checkerboard(cr, image_width, image_height)
        cr.set_source_surface(self._document.surface, 0, 0)
        cr.paint()

        if self._drag_context is not None:
            cr.save()
            self.active_tool.draw_preview(cr, self._drag_context)
            cr.restore()
        cr.restore()

        outline = self.get_color()
        cr.set_source_rgba(outline.red, outline.green, outline.blue, 0.25)
        cr.set_line_width(1)
        cr.rectangle(0.5, 0.5, image_width - 1, image_height - 1)
        cr.stroke()

        accent = self._accent()
        if self._resize_size is not None:
            self._draw_resize_preview(cr, accent, image_width, image_height)
        if self._paste is not None:
            self._draw_paste(cr, accent, image_width, image_height)
        self._draw_handles(cr, accent)

    @staticmethod
    def _accent() -> Gdk.RGBA:
        return Adw.StyleManager.get_default().get_accent_color_rgba()

    def _draw_resize_preview(
        self, cr: cairo.Context, accent: Gdk.RGBA, image_width: int, image_height: int
    ) -> None:
        width, height = self._resize_size
        cr.save()

        # Even-odd over both rectangles tints exactly what is being added or cropped.
        cr.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
        cr.rectangle(0, 0, image_width, image_height)
        cr.rectangle(0, 0, width, height)
        cr.set_source_rgba(accent.red, accent.green, accent.blue, 0.25)
        cr.fill()

        cr.set_source_rgba(accent.red, accent.green, accent.blue, 1.0)
        cr.set_line_width(1)
        cr.set_dash([4, 3])
        cr.rectangle(0.5, 0.5, width - 1, height - 1)
        cr.stroke()
        cr.restore()

    def _draw_paste(
        self, cr: cairo.Context, accent: Gdk.RGBA, image_width: int, image_height: int
    ) -> None:
        paste = self._paste
        cr.save()
        cr.rectangle(paste.x, paste.y, paste.width, paste.height)
        cr.clip()

        # Where the paste overhangs the image, show the white the canvas will grow
        # with, so the preview matches what committing produces.
        cr.save()
        cr.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
        cr.rectangle(paste.x, paste.y, paste.width, paste.height)
        cr.rectangle(0, 0, image_width, image_height)
        cr.set_source_rgb(1, 1, 1)
        cr.fill()
        cr.restore()

        cr.set_source_surface(paste.surface, paste.x, paste.y)
        cr.paint()
        cr.restore()

        cr.save()
        cr.set_source_rgba(accent.red, accent.green, accent.blue, 1.0)
        cr.set_line_width(1)
        cr.set_dash([4, 3])
        cr.rectangle(paste.x + 0.5, paste.y + 0.5, paste.width - 1, paste.height - 1)
        cr.stroke()
        cr.restore()

    def _draw_handles(self, cr: cairo.Context, accent: Gdk.RGBA) -> None:
        half = HANDLE_SIZE / 2
        for hx, hy in self._handles().values():
            cr.rectangle(hx - half, hy - half, HANDLE_SIZE, HANDLE_SIZE)
            cr.set_source_rgba(accent.red, accent.green, accent.blue, 1.0)
            cr.fill_preserve()
            # A white keyline keeps the grip readable on top of dark artwork.
            cr.set_source_rgb(1, 1, 1)
            cr.set_line_width(1)
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
