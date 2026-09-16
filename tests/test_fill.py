# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

import random

import pytest
from gi.repository import Gdk

from hue.document import copy_surface, new_surface, same_pixels
from hue.tools.fill import _premultiplied, flood_fill

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


def reference_flood_fill(surface, x, y, color, tolerance):
    """The original pixel-at-a-time fill, kept as the behaviour to match."""
    width, height = surface.get_width(), surface.get_height()
    if not (0 <= x < width and 0 <= y < height):
        return False
    surface.flush()
    stride = surface.get_stride()
    data = surface.get_data()
    replacement = _premultiplied(color)
    origin = y * stride + x * 4
    target = tuple(data[origin:origin + 4])

    def matches(offset):
        return all(abs(data[offset + i] - target[i]) <= tolerance for i in range(4))

    if all(abs(replacement[i] - target[i]) <= tolerance for i in range(4)):
        return False
    replacement_bytes = bytes(replacement)
    stack = [(x, y)]
    while stack:
        seed_x, seed_y = stack.pop()
        row = seed_y * stride
        if not matches(row + seed_x * 4):
            continue
        left = seed_x
        while left > 0 and matches(row + (left - 1) * 4):
            left -= 1
        right = seed_x
        while right < width - 1 and matches(row + (right + 1) * 4):
            right += 1
        data[row + left * 4:row + (right + 1) * 4] = replacement_bytes * (right - left + 1)
        for neighbour_y in (seed_y - 1, seed_y + 1):
            if not 0 <= neighbour_y < height:
                continue
            neighbour_row = neighbour_y * stride
            scan = left
            while scan <= right:
                if matches(neighbour_row + scan * 4):
                    stack.append((scan, neighbour_y))
                    while scan <= right and matches(neighbour_row + scan * 4):
                        scan += 1
                scan += 1
    surface.mark_dirty()
    return True


def random_image(rng, width, height):
    """Blotches of a few near-identical colours, so regions are ragged and tolerance matters."""
    palette = [(1.0, 1.0, 1.0, 1.0), (0.95, 0.95, 0.95, 1.0), (0.0, 0.0, 0.0, 1.0),
               (0.2, 0.6, 0.2, 1.0), (0.5, 0.5, 0.5, 0.5), (0.0, 0.0, 0.0, 0.0)]
    surface = new_surface(width, height, WHITE)
    for y in range(height):
        for x in range(width):
            if rng.random() < 0.35:
                paint_pixel(surface, x, y, rng.choice(palette))
    return surface


@pytest.mark.parametrize("seed", range(40))
def test_matches_the_original_fill_on_random_images(seed):
    rng = random.Random(seed)
    width, height = rng.randint(1, 23), rng.randint(1, 23)
    image = random_image(rng, width, height)
    x, y = rng.randrange(width), rng.randrange(height)
    color = rgba(rng.random(), rng.random(), rng.random(), rng.choice([1.0, 0.5]))
    tolerance = rng.choice([0, 8, 32, 64, 255])

    expected, actual = copy_surface(image), copy_surface(image)
    assert flood_fill(actual, x, y, color, tolerance) == reference_flood_fill(
        expected, x, y, color, tolerance
    )
    assert same_pixels(actual, expected)


def test_fills_a_region_that_winds_back_on_itself():
    # A spiral corridor: the fill has to turn up, down, left and right to finish.
    surface = new_surface(9, 9, BLACK)
    corridor = [(x, 1) for x in range(1, 8)] + [(7, y) for y in range(1, 8)]
    corridor += [(x, 7) for x in range(1, 8)] + [(1, y) for y in range(3, 8)]
    corridor += [(x, 3) for x in range(1, 6)] + [(5, 5), (5, 4), (4, 5), (3, 5)]
    for x, y in corridor:
        paint_pixel(surface, x, y, WHITE)

    assert flood_fill(surface, 1, 1, rgba(0, 1, 0))

    for x, y in corridor:
        assert pixel_at(surface, x, y) == (0, 255, 0, 255)
    assert pixel_at(surface, 0, 0) == (0, 0, 0, 255)
    assert pixel_at(surface, 2, 5) == (0, 0, 0, 255)
