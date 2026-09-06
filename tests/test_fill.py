# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Gdk

from hue.document import new_surface
from hue.tools.fill import flood_fill

from pixels import paint_pixel, pixel_at

WHITE = (1.0, 1.0, 1.0, 1.0)
BLACK = (0.0, 0.0, 0.0, 1.0)


def rgba(r: float, g: float, b: float, a: float = 1.0) -> Gdk.RGBA:
    color = Gdk.RGBA()
    color.red, color.green, color.blue, color.alpha = r, g, b, a
    return color


def test_fills_a_matching_region_and_stops_at_the_boundary():
    surface = new_surface(4, 4, WHITE)
    for y in range(4):
        paint_pixel(surface, 2, y, BLACK)
        paint_pixel(surface, 3, y, BLACK)

    assert flood_fill(surface, 0, 0, rgba(0, 1, 0))

    assert pixel_at(surface, 0, 0) == (0, 255, 0, 255)
    assert pixel_at(surface, 1, 3) == (0, 255, 0, 255)
    # The black column was never matched, so it is untouched.
    assert pixel_at(surface, 2, 0) == (0, 0, 0, 255)
    assert pixel_at(surface, 3, 3) == (0, 0, 0, 255)


def test_tolerance_widens_what_counts_as_a_match():
    surface = new_surface(2, 1, WHITE)
    paint_pixel(surface, 1, 0, (0.9, 0.9, 0.9, 1.0))

    strict = new_surface(2, 1, WHITE)
    paint_pixel(strict, 1, 0, (0.9, 0.9, 0.9, 1.0))
    flood_fill(strict, 0, 0, rgba(0, 1, 0), tolerance=1)
    assert pixel_at(strict, 0, 0) == (0, 255, 0, 255)
    assert pixel_at(strict, 1, 0) != (0, 255, 0, 255)

    loose = surface
    flood_fill(loose, 0, 0, rgba(0, 1, 0), tolerance=64)
    assert pixel_at(loose, 0, 0) == (0, 255, 0, 255)
    assert pixel_at(loose, 1, 0) == (0, 255, 0, 255)


def test_filling_with_a_color_that_already_matches_is_a_no_op():
    surface = new_surface(2, 2, WHITE)
    assert not flood_fill(surface, 0, 0, rgba(1, 1, 1))
    assert pixel_at(surface, 1, 1) == (255, 255, 255, 255)


def test_out_of_bounds_coordinates_do_nothing():
    surface = new_surface(2, 2, WHITE)
    assert not flood_fill(surface, -1, 0, rgba(0, 1, 0))
    assert not flood_fill(surface, 0, 2, rgba(0, 1, 0))
    assert pixel_at(surface, 0, 0) == (255, 255, 255, 255)
