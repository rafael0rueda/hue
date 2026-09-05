# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass

import cairo
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk

from .clipboard import surface_from_file, surface_from_texture
from .color import ColorState
from .document import MAX_SIZE, Document, crop_surface
from .text import DEFAULT_FONT, TextBox
from .tools import (
    SELECT_TOOL_ID,
    SHAPE_TOOL_IDS,
    TEXT_TOOL_ID,
    Tool,
    ToolContext,
    create_tools,
    draw_marquee,
)

CHECKER_SIZE = 8
HANDLE_SIZE = 10
HANDLE_GRAB = 12
# Room around the image so the grips sitting on its edge are fully visible.
HANDLE_MARGIN = 8
# Breathing room between the typed text and its dashed outline.
TEXT_PADDING = 3
CARET_BLINK_MS = 530
# How far the pointer has to travel before a click inside a text box counts
# as dragging it somewhere else rather than placing the caret.
MOVE_THRESHOLD = 4

HANDLE_CURSORS = {
    "e": "ew-resize",
    "s": "ns-resize",
    "se": "nwse-resize",
    "paste": "move",
    "text": "text",
    "selection": "move",
}


@dataclass
class FloatingPaste:
    """Pasted pixels hovering over the canvas until they are stamped down."""

    surface: cairo.ImageSurface
    x: float = 0.0
    y: float = 0.0
    # Where a lifted selection came from, painted over when the move lands so
    # that vacating the old place and filling the new one is one undo step.
    source: tuple[int, int, int, int] | None = None
    fill: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)

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


@dataclass
class Selection:
    """A rectangle of the image, picked out to be moved, copied or deleted."""

    x: int
    y: int
    width: int
    height: int

    @classmethod
    def from_rect(
        cls, x: float, y: float, width: float, height: float, image_width: int, image_height: int
    ) -> "Selection | None":
        """A selection clipped to the image, or None when nothing is left of it."""
        left = max(0, round(x))
        top = max(0, round(y))
        right = min(image_width, round(x + width))
        bottom = min(image_height, round(y + height))
        if right <= left or bottom <= top:
            return None
        return cls(left, top, right - left, bottom - top)

    @property
    def rect(self) -> tuple[int, int, int, int]:
        return self.x, self.y, self.width, self.height

    def contains(self, x: float, y: float) -> bool:
        return self.x <= x <= self.x + self.width and self.y <= y <= self.y + self.height

    def clamped(self, image_width: int, image_height: int) -> "Selection | None":
        return self.from_rect(self.x, self.y, self.width, self.height, image_width, image_height)


class Canvas(Gtk.DrawingArea):
    """Displays the document and routes pointer input to the active tool."""

    __gsignals__ = {
        "color-picked": (GObject.SignalFlags.RUN_FIRST, None, (Gdk.RGBA, int)),
        "resize-preview": (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
        # A paste or a text box appeared, moved, changed or landed.
        "floating-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        # A selection was made, moved out of, or dropped.
        "selection-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, document: Document, colors: ColorState):
        super().__init__()
        self.colors = colors
        self.tools = create_tools()
        self.active_tool: Tool = self.tools["pencil"]
        self.brush_size = 4
        self.fill_shapes = False
        self.font = DEFAULT_FONT

        self._document: Document | None = None
        self._document_handler = 0
        self._drag_origin: tuple[float, float] | None = None
        self._drag_context: ToolContext | None = None
        self._resize_handle: str | None = None
        self._resize_size: tuple[int, int] | None = None
        self._paste: FloatingPaste | None = None
        self._paste_origin: tuple[float, float] | None = None
        self._text: TextBox | None = None
        self._text_origin: tuple[float, float] | None = None
        self._text_moved = False
        self._selection: Selection | None = None
        self._caret_visible = True
        self._blink_source = 0

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

        # Keys only mean something while something is floating over the canvas,
        # so it takes focus for the duration rather than claiming accelerators.
        self.set_focusable(True)
        self._keys = Gtk.EventControllerKey()
        self._keys.connect("key-pressed", self._on_key_pressed)
        self.add_controller(self._keys)

        # Attached to the key controller only while typing, since an input method
        # swallows every printable key it is offered — including the single-letter
        # tool shortcuts.
        self._im = Gtk.IMMulticontext()
        self._im.set_client_widget(self)
        self._im.connect("commit", self._on_im_commit)

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
        if self._selection is not None:
            document = self._document
            self.set_selection(self._selection.clamped(document.width, document.height))
        self._sync_content_size()
        self.queue_draw()

    def _sync_content_size(self) -> None:
        width, height = self._document.width, self._document.height
        if self._resize_size is not None:
            # Follow the drag so the pending outline stays inside the widget.
            width = max(width, self._resize_size[0])
            height = max(height, self._resize_size[1])
        bounds = self._floating_bounds()
        if bounds is not None:
            # A screenshot hanging off the edge stays visible before it lands.
            float_x, float_y, float_width, float_height = bounds
            width = max(width, round(float_x) + float_width)
            height = max(height, round(float_y) + float_height)
        self.set_content_width(width + HANDLE_MARGIN)
        self.set_content_height(height + HANDLE_MARGIN)

    def select_tool(self, tool_id: str) -> None:
        self.active_tool = self.tools[tool_id]
        # A selection outlives the tool that made it: Cut, Copy and Delete keep
        # working on it, and going back to the select tool picks it up again.

    @property
    def supports_fill(self) -> bool:
        return self.active_tool.id in SHAPE_TOOL_IDS

    @property
    def supports_font(self) -> bool:
        return self.active_tool.id == TEXT_TOOL_ID

    def set_font(self, font: str) -> None:
        self.font = font
        if self._text is not None:
            self._text.font = font
            # The font button stole the focus on its way here.
            self.grab_focus()
            self._refresh_text()

    # Selection

    @property
    def selecting(self) -> bool:
        """Whether the select tool is the one holding the pointer."""
        return self.active_tool.id == SELECT_TOOL_ID

    @property
    def has_selection(self) -> bool:
        return self._selection is not None

    def set_selection(self, selection: Selection | None) -> None:
        if selection == self._selection:
            return
        self._selection = selection
        self.queue_draw()
        self.emit("selection-changed")

    def select_region(self, x: float, y: float, width: float, height: float) -> None:
        """Take the rectangle the select tool just dragged out."""
        self.set_selection(
            Selection.from_rect(x, y, width, height, self._document.width, self._document.height)
        )
        if self._selection is not None:
            # Esc and Delete belong to the selection from here on.
            self.grab_focus()

    def _selection_at(self, x: float, y: float) -> "Selection | None":
        """The selection under a point, when the select tool is there to grab it."""
        if not self.selecting or self._selection is None:
            return None
        return self._selection if self._selection.contains(x, y) else None

    def clear_selection(self) -> bool:
        if self._selection is None:
            return False
        self.set_selection(None)
        return True

    def selection_surface(self) -> cairo.ImageSurface | None:
        """A copy of the selected pixels, for the clipboard."""
        if self._selection is None:
            return None
        return crop_surface(self._document.surface, *self._selection.rect)

    def delete_selection(self) -> bool:
        if self._selection is None:
            return False
        self._document.erase(self._selection.rect, self._erase_fill())
        self.set_selection(None)
        return True

    def _erase_fill(self) -> tuple[float, float, float, float]:
        # Moving or deleting a selection leaves the background colour behind, the
        # same colour the eraser paints with.
        color = self.colors.secondary
        return color.red, color.green, color.blue, color.alpha

    def _lift_selection(self, copy: bool) -> None:
        """Float the selected pixels so the drag can carry them somewhere else."""
        selection = self._selection
        surface = crop_surface(self._document.surface, *selection.rect)
        self.set_selection(None)
        self.begin_paste(
            surface,
            selection.x,
            selection.y,
            source=None if copy else selection.rect,
            fill=self._erase_fill(),
        )

    # Floating paste and text

    @property
    def has_floating(self) -> bool:
        return self._paste is not None or self._text is not None

    @property
    def is_typing(self) -> bool:
        return self._text is not None

    def _floating_bounds(self) -> tuple[float, float, int, int] | None:
        """Where the pending paste or text sits, or None when nothing floats."""
        if self._paste is not None:
            return self._paste.x, self._paste.y, self._paste.width, self._paste.height
        if self._text is not None:
            width, height = self._text.size
            if width > 0 and height > 0:
                return self._text.x, self._text.y, width, height
        return None

    @property
    def pending_size(self) -> tuple[int, int]:
        """The canvas size a commit would leave behind, for the size readout."""
        width, height = self._document.width, self._document.height
        bounds = self._floating_bounds()
        if bounds is None:
            return width, height
        float_x, float_y, float_width, float_height = bounds
        return (
            min(max(width, round(float_x) + float_width), MAX_SIZE),
            min(max(height, round(float_y) + float_height), MAX_SIZE),
        )

    def commit_floating(self) -> bool:
        """Land whatever hovers over the canvas — only ever one thing does."""
        return self.commit_text() or self.commit_paste()

    def cancel_floating(self) -> bool:
        return self.cancel_text() or self.cancel_paste()

    def begin_paste(
        self,
        surface: cairo.ImageSurface,
        x: float = 0,
        y: float = 0,
        source: tuple[int, int, int, int] | None = None,
        fill: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
    ) -> None:
        """Float an image over the canvas until it is committed or discarded."""
        self.commit_floating()
        # Whatever was selected is not what is about to hover over the canvas.
        self.set_selection(None)
        self._paste = FloatingPaste(surface, source=source, fill=fill)
        self._paste.move_to(x, y)
        self.grab_focus()
        self._sync_content_size()
        self.queue_draw()
        self.emit("floating-changed")

    def commit_paste(self) -> bool:
        """Stamp the floating image into the document, growing the canvas to fit."""
        if self._paste is None:
            return False
        paste, self._paste = self._paste, None
        self._document.paste(
            paste.surface,
            round(paste.x),
            round(paste.y),
            erase=paste.source,
            erase_fill=paste.fill,
        )
        self._sync_content_size()
        self.queue_draw()
        self.emit("floating-changed")
        return True

    def cancel_paste(self) -> bool:
        if self._paste is None:
            return False
        self._paste = None
        self._sync_content_size()
        self.queue_draw()
        self.emit("floating-changed")
        return True

    def begin_text(self, x: float, y: float, color: Gdk.RGBA) -> None:
        """Start a text box at a point on the canvas and take keyboard input."""
        self.commit_floating()
        self._text = TextBox(x, y, color, self.font)
        self.grab_focus()
        self._keys.set_im_context(self._im)
        self._im.focus_in()
        self._start_blink()
        self._sync_content_size()
        self.queue_draw()
        self.emit("floating-changed")

    def commit_text(self) -> bool:
        """Rasterise the typed text into the image, growing the canvas to fit."""
        if self._text is None:
            return False
        text, self._text = self._text, None
        surface = text.render_surface()
        if surface is not None:
            self._document.paste(surface, round(text.x), round(text.y))
        self._end_typing()
        return True

    def cancel_text(self) -> bool:
        if self._text is None:
            return False
        self._text = None
        self._end_typing()
        return True

    def _end_typing(self) -> None:
        self._text_origin = None
        self._text_moved = False
        self._stop_blink()
        self._im.focus_out()
        self._keys.set_im_context(None)
        self._sync_content_size()
        self.queue_draw()
        self.emit("floating-changed")

    def _refresh_text(self) -> None:
        # A solid caret reads better than one caught mid-blink while the box is
        # being worked on.
        self._caret_visible = True
        self._sync_content_size()
        self.queue_draw()
        self.emit("floating-changed")

    def _start_blink(self) -> None:
        self._caret_visible = True
        if self._blink_source == 0:
            self._blink_source = GLib.timeout_add(CARET_BLINK_MS, self._blink)

    def _blink(self) -> bool:
        if self._text is None:
            self._blink_source = 0
            return GLib.SOURCE_REMOVE
        self._caret_visible = not self._caret_visible
        self.queue_draw()
        return GLib.SOURCE_CONTINUE

    def _stop_blink(self) -> None:
        if self._blink_source:
            GLib.source_remove(self._blink_source)
            self._blink_source = 0

    def _on_im_commit(self, im, text: str) -> None:
        if self._text is None:
            return
        self._text.insert(text)
        self._refresh_text()

    def _on_key_pressed(self, controller, keyval, keycode, state) -> bool:
        if self._text is not None:
            return self._on_text_key(keyval, state)
        if self._paste is not None:
            if keyval == Gdk.KEY_Escape:
                return self.cancel_paste()
            if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
                return self.commit_paste()
            return False
        if self._selection is not None:
            if keyval == Gdk.KEY_Escape:
                return self.clear_selection()
            if keyval in (Gdk.KEY_Delete, Gdk.KEY_KP_Delete, Gdk.KEY_BackSpace):
                return self.delete_selection()
        return False

    def _on_text_key(self, keyval: int, state: Gdk.ModifierType) -> bool:
        """The editing keys; typed characters arrive through the input method."""
        text = self._text
        if keyval == Gdk.KEY_Escape:
            return self.cancel_text()
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_ISO_Enter):
            # Return is a new line inside a text box, so landing it takes Ctrl.
            if state & Gdk.ModifierType.CONTROL_MASK:
                return self.commit_text()
            text.insert("\n")
        elif keyval == Gdk.KEY_BackSpace:
            text.backspace()
        elif keyval == Gdk.KEY_Delete:
            text.delete()
        elif keyval in (Gdk.KEY_Left, Gdk.KEY_KP_Left):
            text.move_caret(-1)
        elif keyval in (Gdk.KEY_Right, Gdk.KEY_KP_Right):
            text.move_caret(1)
        elif keyval in (Gdk.KEY_Up, Gdk.KEY_KP_Up):
            text.move_caret_line(-1)
        elif keyval in (Gdk.KEY_Down, Gdk.KEY_KP_Down):
            text.move_caret_line(1)
        elif keyval in (Gdk.KEY_Home, Gdk.KEY_KP_Home):
            text.move_caret_to_edge(False)
        elif keyval in (Gdk.KEY_End, Gdk.KEY_KP_End):
            text.move_caret_to_edge(True)
        else:
            # Ctrl+Z, Ctrl+S and the rest still belong to the window.
            return False
        self._refresh_text()
        return True

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
        if self.has_floating:
            # The paste or text box owns the pointer until it lands.
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
        if self._text is not None and self._text.contains(x, y, TEXT_PADDING):
            self._set_cursor("text")
            return
        if self._selection_at(x, y) is not None:
            self._set_cursor("selection")
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
            begin_text=self.begin_text,
            select_region=self.select_region,
        )

    def _on_drag_begin(self, gesture, start_x, start_y):
        self._drag_origin = (start_x, start_y)

        if self._text is not None:
            if self._text.contains(start_x, start_y, TEXT_PADDING):
                self._text_origin = (self._text.x, self._text.y)
                self._text_moved = False
                self.grab_focus()
            else:
                # Clicking away lands the text; the click itself does not draw.
                self.commit_text()
            return

        if self._paste is not None:
            if self._paste.contains(start_x, start_y):
                self._paste_origin = (self._paste.x, self._paste.y)
                self._set_cursor("paste")
            else:
                # Clicking away lands the paste; the click itself does not draw.
                self.commit_paste()
            return

        # Only the select tool picks the pixels up; the others paint over them.
        if self._selection_at(start_x, start_y) is not None:
            # Ctrl leaves the original where it is, so the drag copies instead of moves.
            state = gesture.get_current_event_state()
            self._lift_selection(bool(state & Gdk.ModifierType.CONTROL_MASK))
            self._paste_origin = (self._paste.x, self._paste.y)
            self._set_cursor("paste")
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

        if self._text_origin is not None:
            if not self._text_moved and max(abs(offset_x), abs(offset_y)) < MOVE_THRESHOLD:
                # Still small enough to be the wobble of a click placing the caret.
                return
            self._text_moved = True
            self._text.move_to(self._text_origin[0] + offset_x, self._text_origin[1] + offset_y)
            self._refresh_text()
            return

        if self._paste_origin is not None:
            self._paste.move_to(self._paste_origin[0] + offset_x, self._paste_origin[1] + offset_y)
            self._sync_content_size()
            self.queue_draw()
            self.emit("floating-changed")
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

        if self._text_origin is not None:
            if not self._text_moved:
                # A click rather than a drag: put the caret where it landed.
                self._text.caret_at(x, y)
            self._text_origin = None
            self._text_moved = False
            self._drag_origin = None
            self._refresh_text()
            return

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
        if self._text is not None:
            self._draw_text(cr, accent, image_width, image_height)
        if self._selection is not None:
            draw_marquee(cr, *self._selection.rect)
        self._draw_handles(cr, accent)

    @staticmethod
    def _accent() -> Gdk.RGBA:
        return Adw.StyleManager.get_default().get_accent_color_rgba()

    @staticmethod
    def _draw_dashed_rect(
        cr: cairo.Context, accent: Gdk.RGBA, x: float, y: float, width: float, height: float
    ) -> None:
        cr.save()
        cr.set_source_rgba(accent.red, accent.green, accent.blue, 1.0)
        cr.set_line_width(1)
        cr.set_dash([4, 3])
        cr.rectangle(x + 0.5, y + 0.5, width - 1, height - 1)
        cr.stroke()
        cr.restore()

    @staticmethod
    def _draw_overhang(
        cr: cairo.Context,
        x: float,
        y: float,
        width: float,
        height: float,
        image_width: int,
        image_height: int,
    ) -> None:
        """Fill the part of a rectangle that hangs off the image with white.

        That is the colour the canvas grows with, so the preview of a paste or a
        text box matches what committing it produces.
        """
        cr.save()
        cr.rectangle(x, y, width, height)
        cr.clip()
        # Even-odd over both rectangles leaves exactly the overhanging part.
        cr.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
        cr.rectangle(x, y, width, height)
        cr.rectangle(0, 0, image_width, image_height)
        cr.set_source_rgb(1, 1, 1)
        cr.fill()
        cr.restore()

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
        cr.restore()

        self._draw_dashed_rect(cr, accent, 0, 0, width, height)

    def _draw_paste(
        self, cr: cairo.Context, accent: Gdk.RGBA, image_width: int, image_height: int
    ) -> None:
        paste = self._paste
        if paste.source is not None:
            # The pixels are on their way out of here; show the place they leave behind.
            cr.save()
            cr.set_source_rgba(*paste.fill)
            cr.rectangle(*paste.source)
            cr.fill()
            cr.restore()

        self._draw_overhang(
            cr, paste.x, paste.y, paste.width, paste.height, image_width, image_height
        )

        cr.save()
        cr.rectangle(paste.x, paste.y, paste.width, paste.height)
        cr.clip()
        cr.set_source_surface(paste.surface, paste.x, paste.y)
        cr.paint()
        cr.restore()

        self._draw_dashed_rect(cr, accent, paste.x, paste.y, paste.width, paste.height)

    def _draw_text(
        self, cr: cairo.Context, accent: Gdk.RGBA, image_width: int, image_height: int
    ) -> None:
        text = self._text
        width, height = text.size
        if width > 0 and height > 0:
            self._draw_overhang(cr, text.x, text.y, width, height, image_width, image_height)
            text.render(cr)

        # The outline sits outside the glyphs, and outside what gets rasterised.
        self._draw_dashed_rect(
            cr,
            accent,
            text.x - TEXT_PADDING,
            text.y - TEXT_PADDING,
            width + 2 * TEXT_PADDING,
            height + 2 * TEXT_PADDING,
        )

        if self._caret_visible:
            caret_x, caret_y, caret_height = text.caret_rect()
            cr.set_source_rgba(
                text.color.red, text.color.green, text.color.blue, text.color.alpha
            )
            cr.rectangle(caret_x, caret_y, 1, caret_height)
            cr.fill()

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
