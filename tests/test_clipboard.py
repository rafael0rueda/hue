# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from gi.repository import Gdk, GLib, GObject

from tempera.clipboard import (
    NO_IMAGE,
    has_image,
    read_image,
    surface_from_texture,
    texture_from_surface,
)
from tempera.document import MAX_SIZE, new_surface

from pixels import paint_pixel, pixel_at


class FakeClipboard:
    """Just enough of Gdk.Clipboard for has_image(), without touching the real one."""

    def __init__(self, *gtypes):
        builder = Gdk.ContentFormatsBuilder.new()
        for gtype in gtypes:
            builder.add_gtype(gtype)
        self._formats = builder.to_formats()

    def get_formats(self):
        return self._formats


class TextureClipboard:
    """Answers read_texture_async() at once, with a texture or with a failure."""

    def __init__(self, texture=None):
        self._texture = texture

    def read_texture_async(self, cancellable, callback):
        callback(self, None)

    def read_texture_finish(self, result):
        if self._texture is None:
            raise GLib.Error("no texture")
        return self._texture

    def read_value_async(self, gtype, priority, cancellable, callback):
        callback(self, None)

    def read_value_finish(self, result):
        raise GLib.Error("no file either")


def wide_texture(width: int) -> Gdk.Texture:
    pixels = GLib.Bytes.new(b"\xff" * width * 4)
    return Gdk.MemoryTexture.new(width, 1, Gdk.MemoryFormat.B8G8R8A8_PREMULTIPLIED, pixels, width * 4)


def test_has_image_true_for_a_texture():
    assert has_image(FakeClipboard(Gdk.Texture))


def test_has_image_false_for_plain_text():
    assert not has_image(FakeClipboard(GObject.TYPE_STRING))


def test_texture_round_trips_surface_pixels():
    surface = new_surface(2, 2, (1.0, 1.0, 1.0, 1.0))
    paint_pixel(surface, 1, 0, (1.0, 0.0, 0.0, 1.0))

    texture = texture_from_surface(surface)
    assert (texture.get_width(), texture.get_height()) == (2, 2)

    round_tripped = surface_from_texture(texture)
    assert pixel_at(round_tripped, 0, 0) == (255, 255, 255, 255)
    assert pixel_at(round_tripped, 1, 0) == (255, 0, 0, 255)


def test_surface_from_texture_refuses_one_wider_than_a_canvas_can_be():
    with pytest.raises(GLib.Error, match="Too large"):
        surface_from_texture(wide_texture(MAX_SIZE + 1))


def test_read_image_explains_an_oversized_clipboard_image():
    images, errors = [], []
    read_image(TextureClipboard(wide_texture(MAX_SIZE + 1)), images.append, errors.append)
    assert images == []
    assert len(errors) == 1 and "Too large" in errors[0]


def test_read_image_reports_an_empty_clipboard():
    images, errors = [], []
    read_image(TextureClipboard(), images.append, errors.append)
    assert (images, errors) == ([], [NO_IMAGE])
