from __future__ import annotations

import cairo
from gi.repository import Gdk, GdkPixbuf, GObject

MAX_UNDO = 50
DEFAULT_WIDTH = 800
DEFAULT_HEIGHT = 600


def new_surface(width: int, height: int, fill=(1.0, 1.0, 1.0, 1.0)) -> cairo.ImageSurface:
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    cr = cairo.Context(surface)
    cr.set_operator(cairo.OPERATOR_SOURCE)
    cr.set_source_rgba(*fill)
    cr.paint()
    return surface


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

    @classmethod
    def from_pixbuf(cls, pixbuf: GdkPixbuf.Pixbuf) -> "Document":
        surface = new_surface(pixbuf.get_width(), pixbuf.get_height(), (0, 0, 0, 0))
        cr = cairo.Context(surface)
        Gdk.cairo_set_source_pixbuf(cr, pixbuf, 0, 0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        return cls(surface)

    def to_pixbuf(self) -> GdkPixbuf.Pixbuf:
        self.surface.flush()
        return Gdk.pixbuf_get_from_surface(self.surface, 0, 0, self.width, self.height)
