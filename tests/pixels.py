# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

"""Small pixel-reading helpers shared by the surface-based tests."""

import cairo


def pixel_at(surface: cairo.ImageSurface, x: int, y: int) -> tuple[int, int, int, int]:
    """(r, g, b, a) at a pixel, from cairo's premultiplied BGRA bytes.

    Only accurate for fully opaque fills, where premultiplied and straight
    alpha are the same numbers — which is all these tests use.
    """
    surface.flush()
    stride = surface.get_stride()
    data = surface.get_data()
    offset = y * stride + x * 4
    b, g, r, a = data[offset], data[offset + 1], data[offset + 2], data[offset + 3]
    return (r, g, b, a)


def paint_pixel(surface: cairo.ImageSurface, x: int, y: int, color) -> None:
    cr = cairo.Context(surface)
    cr.set_operator(cairo.OPERATOR_SOURCE)
    cr.set_source_rgba(*color)
    cr.rectangle(x, y, 1, 1)
    cr.fill()
