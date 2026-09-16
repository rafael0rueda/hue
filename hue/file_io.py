# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import os

import cairo
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk

from .document import MAX_SIZE, Document, new_surface, surface_from_pixbuf

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
# The ICO format stores its size in a byte, where 0 means 256.
ICO_MAX_SIZE = 256
DEFAULT_EXTENSION = ".png"
LOAD_CHUNK = 64 * 1024


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


def image_error(message: str) -> GLib.Error:
    """A failure to read or write an image, raised the way GdkPixbuf reports its own."""
    return GLib.Error.new_literal(Gio.io_error_quark(), message, Gio.IOErrorEnum.FAILED)


def fits(width: int, height: int) -> bool:
    return width <= MAX_SIZE and height <= MAX_SIZE


def check_image_size(width: int, height: int) -> None:
    """Refuse an image bigger than a canvas can be, before its pixels are copied."""
    if not fits(width, height):
        # Short enough for a toast at the window's default width.
        raise image_error(f"Too large at {width} × {height} px (the limit is {MAX_SIZE})")


def load_surface(file: Gio.File) -> cairo.ImageSurface:
    """Decode an image file into a surface, raising GLib.Error when it cannot be.

    A small file can declare enormous dimensions, so the size is checked as soon
    as the loader has read the header rather than after decoding gigabytes.
    """
    if file.get_path() is None:
        # Hue stays offline, so a web or network address is never fetched.
        raise image_error(f"“{file.get_basename()}” is not a file on this computer")

    declared = (0, 0)

    def on_size_prepared(loader, width, height):
        nonlocal declared
        declared = (width, height)
        if not fits(width, height):
            # The loader goes on to decode into whatever size is set here, so
            # shrink it to nothing rather than let it allocate the real thing.
            loader.set_size(1, 1)

    # Opened first: a loader that is never closed warns when it is freed.
    stream = file.read(None)
    loader = GdkPixbuf.PixbufLoader()
    loader.connect("size-prepared", on_size_prepared)
    try:
        while fits(*declared):
            chunk = stream.read_bytes(LOAD_CHUNK, None)
            if chunk.get_size() == 0:
                break
            loader.write_bytes(chunk)
        loader.close()
    except GLib.Error:
        # Closing twice is harmless.
        try:
            loader.close()
        except GLib.Error:
            pass
        # Cutting a too-large image short is expected to upset the decoder.
        if fits(*declared):
            raise
    finally:
        stream.close(None)

    check_image_size(*declared)
    return surface_from_pixbuf(loader.get_pixbuf())


def load_document(file: Gio.File) -> Document:
    document = Document(load_surface(file))
    document.file = file
    return document


def with_default_extension(file: Gio.File) -> Gio.File:
    """The file to save to, with .png added when the name has no extension at all.

    Without one the image would still be written as PNG, but under a name that
    neither the file manager nor Hue's own Open dialog recognises as an image.
    """
    name = file.get_basename()
    if os.path.splitext(name)[1]:
        return file
    return file.get_parent().get_child(name + DEFAULT_EXTENSION)


def format_for(file: Gio.File) -> str:
    extension = os.path.splitext(file.get_path())[1].lower()
    return EXTENSION_FORMATS.get(extension, "png")


def save_document(document: Document, file: Gio.File, quality: int = 90) -> None:
    image_format = format_for(file)
    if image_format == "ico" and max(document.width, document.height) > ICO_MAX_SIZE:
        raise image_error(f"ICO images can be at most {ICO_MAX_SIZE} × {ICO_MAX_SIZE} px")

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

    options = (["quality"], [str(quality)]) if image_format == "jpeg" else ([], [])
    # Encoded in memory first, then swapped in whole: writing straight to the
    # file would truncate the original before an encoder or a full disk failed.
    _ok, data = pixbuf.save_to_bufferv(image_format, *options)
    file.replace_contents(data, None, False, Gio.FileCreateFlags.NONE, None)
    document.file = file
    document.modified = False
    document.emit("state-changed")
