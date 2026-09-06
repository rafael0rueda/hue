# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Gdk, GObject

from hue.clipboard import has_image, surface_from_texture, texture_from_surface
from hue.document import new_surface

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
