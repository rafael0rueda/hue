# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import cairo
from gi.repository import Gdk

from .base import Tool, ToolContext

TOLERANCE = 32


def _premultiplied(color: Gdk.RGBA) -> tuple[int, int, int, int]:
    alpha = color.alpha
    return (
        round(color.blue * alpha * 255),
        round(color.green * alpha * 255),
        round(color.red * alpha * 255),
        round(alpha * 255),
    )


def flood_fill(surface: cairo.ImageSurface, x: int, y: int, color: Gdk.RGBA,
               tolerance: int = TOLERANCE) -> bool:
    """Scanline flood fill over the surface's ARGB32 buffer."""
    width, height = surface.get_width(), surface.get_height()
    if not (0 <= x < width and 0 <= y < height):
        return False

    surface.flush()
    stride = surface.get_stride()
    data = surface.get_data()
    replacement = _premultiplied(color)

    origin = y * stride + x * 4
    target = tuple(data[origin:origin + 4])

    def matches(offset: int) -> bool:
        return all(abs(data[offset + i] - target[i]) <= tolerance for i in range(4))

    # Filling with a colour that still matches the target would never terminate.
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


class FillTool(Tool):
    id = "fill"
    label = "Fill"
    icon_name = "hue-fill-symbolic"

    def press(self, ctx: ToolContext, x, y):
        flood_fill(ctx.surface, int(x), int(y), ctx.color)
