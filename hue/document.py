# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import cairo
from gi.repository import Gdk, GdkPixbuf, GObject

MAX_UNDO = 50
DEFAULT_WIDTH = 800
DEFAULT_HEIGHT = 600
MAX_SIZE = 8192


def new_surface(width: int, height: int, fill=(1.0, 1.0, 1.0, 1.0)) -> cairo.ImageSurface:
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    cr = cairo.Context(surface)
    cr.set_operator(cairo.OPERATOR_SOURCE)
    cr.set_source_rgba(*fill)
    cr.paint()
    return surface


def surface_from_pixbuf(pixbuf: GdkPixbuf.Pixbuf) -> cairo.ImageSurface:
    """Copy a pixbuf into a surface Hue can draw on."""
    surface = new_surface(pixbuf.get_width(), pixbuf.get_height(), (0, 0, 0, 0))
    cr = cairo.Context(surface)
    Gdk.cairo_set_source_pixbuf(cr, pixbuf, 0, 0)
    cr.set_operator(cairo.OPERATOR_SOURCE)
    cr.paint()
    return surface


def crop_surface(
    src: cairo.ImageSurface, x: int, y: int, width: int, height: int
) -> cairo.ImageSurface:
    """A copy of one rectangle of a surface, for lifting a selection out of it."""
    dst = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    cr = cairo.Context(dst)
    cr.set_operator(cairo.OPERATOR_SOURCE)
    cr.set_source_surface(src, -x, -y)
    cr.paint()
    return dst


def copy_surface(src: cairo.ImageSurface) -> cairo.ImageSurface:
    dst = cairo.ImageSurface(cairo.FORMAT_ARGB32, src.get_width(), src.get_height())
    cr = cairo.Context(dst)
    cr.set_operator(cairo.OPERATOR_SOURCE)
    cr.set_source_surface(src, 0, 0)
    cr.paint()
    return dst


class Document(GObject.Object):
    """The painted image plus its undo history."""

    __gsignals__ = {
        "content-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "state-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, surface: cairo.ImageSurface | None = None):
        super().__init__()
        self.surface = surface or new_surface(DEFAULT_WIDTH, DEFAULT_HEIGHT)
        self.file = None
        self.modified = False
        self._undo: list[cairo.ImageSurface] = []
        self._redo: list[cairo.ImageSurface] = []

    @property
    def width(self) -> int:
        return self.surface.get_width()

    @property
    def height(self) -> int:
        return self.surface.get_height()

    @property
    def title(self) -> str:
        return self.file.get_basename() if self.file else "Untitled"

    def begin_change(self) -> None:
        """Snapshot the surface so the coming edit can be undone."""
        self._undo.append(copy_surface(self.surface))
        del self._undo[:-MAX_UNDO]
        self._redo.clear()

    def commit_change(self) -> None:
        self.modified = True
        self.emit("content-changed")
        self.emit("state-changed")

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def undo(self) -> None:
        if not self._undo:
            return
        self._redo.append(copy_surface(self.surface))
        self.surface = self._undo.pop()
        self.commit_change()

    def redo(self) -> None:
        if not self._redo:
            return
        self._undo.append(copy_surface(self.surface))
        self.surface = self._redo.pop()
        self.commit_change()

    def _resized_surface(
        self, width: int, height: int, fill=(1.0, 1.0, 1.0, 1.0)
    ) -> cairo.ImageSurface:
        """The current image on a differently sized canvas, anchored top-left."""
        surface = new_surface(width, height, fill)
        cr = cairo.Context(surface)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_surface(self.surface, 0, 0)
        cr.rectangle(0, 0, min(width, self.width), min(height, self.height))
        cr.fill()
        return surface

    def resize(self, width: int, height: int, fill=(1.0, 1.0, 1.0, 1.0)) -> None:
        """Grow or crop the canvas, keeping the existing pixels anchored top-left."""
        width = max(1, min(int(width), MAX_SIZE))
        height = max(1, min(int(height), MAX_SIZE))
        if width == self.width and height == self.height:
            return

        self.begin_change()
        self.surface = self._resized_surface(width, height, fill)
        self.commit_change()

    def _fill_rect(self, rect: tuple[int, int, int, int], fill) -> None:
        cr = cairo.Context(self.surface)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(*fill)
        cr.rectangle(*rect)
        cr.fill()

    def erase(self, rect: tuple[int, int, int, int], fill=(1.0, 1.0, 1.0, 1.0)) -> None:
        """Paint one rectangle over with the colour the canvas is made of."""
        self.begin_change()
        self._fill_rect(rect, fill)
        self.commit_change()

    def paste(
        self,
        image: cairo.ImageSurface,
        x: int = 0,
        y: int = 0,
        erase: tuple[int, int, int, int] | None = None,
    ) -> None:
        """Stamp an image onto the canvas, growing it if the image runs off the edge.

        The growth, the optional erase of where the pixels came from, and the stamp
        share one undo entry, so a single undo takes back a whole move.
        """
        x, y = max(0, int(x)), max(0, int(y))
        width = min(max(self.width, x + image.get_width()), MAX_SIZE)
        height = min(max(self.height, y + image.get_height()), MAX_SIZE)

        self.begin_change()
        if (width, height) != (self.width, self.height):
            self.surface = self._resized_surface(width, height)
        if erase is not None:
            # Where a moved selection came from, left the same white a bigger
            # canvas is made of.
            self._fill_rect(erase, (1.0, 1.0, 1.0, 1.0))
        cr = cairo.Context(self.surface)
        cr.set_source_surface(image, x, y)
        cr.paint()
        self.commit_change()

    @classmethod
    def from_pixbuf(cls, pixbuf: GdkPixbuf.Pixbuf) -> "Document":
        return cls(surface_from_pixbuf(pixbuf))

    def to_pixbuf(self) -> GdkPixbuf.Pixbuf:
        self.surface.flush()
        return Gdk.pixbuf_get_from_surface(self.surface, 0, 0, self.width, self.height)
