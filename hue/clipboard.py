# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import Callable

import cairo
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, GObject

from .document import surface_from_pixbuf

NO_IMAGE = "No image in the clipboard"

# Everything Hue knows how to turn into pixels, in the order it is worth trying.
IMAGE_TYPES = (Gdk.Texture, Gdk.FileList, Gio.File)


def surface_from_texture(texture: Gdk.Texture) -> cairo.ImageSurface:
    """Copy a clipboard or drag-and-drop texture into a surface.

    Gdk.Texture.download() cannot be used from Python — PyGObject hands the
    texture a copy of the buffer, so the pixels never reach us — hence the
    detour through GdkPixbuf.
    """
    return surface_from_pixbuf(Gdk.pixbuf_get_from_texture(texture))


def texture_from_surface(surface: cairo.ImageSurface) -> Gdk.Texture:
    """Wrap a surface as a texture other applications can paste."""
    surface.flush()
    return Gdk.MemoryTexture.new(
        surface.get_width(),
        surface.get_height(),
        # Cairo's ARGB32 is exactly this byte order on little-endian machines.
        Gdk.MemoryFormat.B8G8R8A8_PREMULTIPLIED,
        GLib.Bytes.new(bytes(surface.get_data())),
        surface.get_stride(),
    )


def surface_from_file(file: Gio.File) -> cairo.ImageSurface:
    return surface_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file(file.get_path()))


def has_image(clipboard: Gdk.Clipboard) -> bool:
    """Whether pasting would produce anything, used to grey out the action."""
    # Other applications advertise mime types, so fold in whatever GTK knows how
    # to deserialize first. What comes back names concrete classes such as
    # GdkMemoryTexture or GLocalFile, which contain_gtype() will not match
    # against the base types, hence the subclass check.
    formats = clipboard.get_formats().union_deserialize_gtypes()
    return any(
        GObject.type_is_a(gtype, image_type)
        for gtype in formats.get_gtypes()
        for image_type in IMAGE_TYPES
    )


def read_image(
    clipboard: Gdk.Clipboard,
    on_image: Callable[[cairo.ImageSurface], None],
    on_error: Callable[[str], None],
) -> None:
    """Fetch the clipboard image, falling back to a copied image file."""

    def on_texture(source, result):
        try:
            on_image(surface_from_texture(source.read_texture_finish(result)))
            return
        except (GLib.Error, TypeError):
            pass
        # Copying a file in Files puts paths on the clipboard rather than pixels.
        clipboard.read_value_async(Gio.File, GLib.PRIORITY_DEFAULT, None, on_file)

    def on_file(source, result):
        try:
            on_image(surface_from_file(source.read_value_finish(result)))
        except (GLib.Error, TypeError):
            on_error(NO_IMAGE)

    clipboard.read_texture_async(None, on_texture)
