from __future__ import annotations

import os

import cairo
from gi.repository import Gdk, GdkPixbuf, Gio, Gtk

from .document import Document, new_surface

EXTENSION_FORMATS = {
    ".png": "png",
    ".jpg": "jpeg",
    ".jpeg": "jpeg",
    ".bmp": "bmp",
    ".tiff": "tiff",
    ".tif": "tiff",
    ".webp": "webp",
    ".ico": "ico",
}
FLATTEN_FORMATS = {"jpeg", "bmp"}


def image_filters() -> Gio.ListStore:
    store = Gio.ListStore.new(Gtk.FileFilter)

    images = Gtk.FileFilter(name="Images")
    for mime in ("image/png", "image/jpeg", "image/bmp", "image/tiff", "image/webp"):
        images.add_mime_type(mime)
    store.append(images)

    png = Gtk.FileFilter(name="PNG image")
    png.add_mime_type("image/png")
    store.append(png)

    every = Gtk.FileFilter(name="All files")
    every.add_pattern("*")
    store.append(every)
    return store


def load_document(file: Gio.File) -> Document:
    pixbuf = GdkPixbuf.Pixbuf.new_from_file(file.get_path())
    document = Document.from_pixbuf(pixbuf)
    document.file = file
    return document


def format_for(file: Gio.File) -> str:
    extension = os.path.splitext(file.get_path())[1].lower()
    return EXTENSION_FORMATS.get(extension, "png")


def save_document(document: Document, file: Gio.File) -> None:
    image_format = format_for(file)

    if image_format in FLATTEN_FORMATS:
        # These formats have no alpha channel, so composite onto white first.
        flattened = new_surface(document.width, document.height)
        cr = cairo.Context(flattened)
        cr.set_source_surface(document.surface, 0, 0)
        cr.paint()
        flattened.flush()
        with_alpha = Gdk.pixbuf_get_from_surface(flattened, 0, 0, document.width, document.height)
        # These encoders reject an alpha channel outright, so drop it.
        pixbuf = GdkPixbuf.Pixbuf.new(
            GdkPixbuf.Colorspace.RGB, False, 8, document.width, document.height
        )
        pixbuf.fill(0xFFFFFFFF)
        with_alpha.composite(
            pixbuf, 0, 0, document.width, document.height,
            0, 0, 1, 1, GdkPixbuf.InterpType.NEAREST, 255,
        )
    else:
        pixbuf = document.to_pixbuf()

    pixbuf.savev(file.get_path(), image_format, [], [])
    document.file = file
    document.modified = False
    document.emit("state-changed")
