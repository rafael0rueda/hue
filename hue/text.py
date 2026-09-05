# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import cairo
from gi.repository import Gdk, Pango, PangoCairo

DEFAULT_FONT = "Sans 24"
# What the size slider offers for text: small enough for a caption, large enough
# for a title across the canvas.
FONT_SIZE_RANGE = (6, 200)

# The pixels that end up in the image must not depend on the desktop's text
# scaling, so every layout Hue lays out comes from a font map pinned at the
# usual 96 dpi rather than from the screen's.
_FONT_MAP = PangoCairo.FontMap.new()
_FONT_MAP.set_resolution(96)


def font_size(font: str) -> int:
    """The point size of a font description, as the size slider counts it."""
    return max(1, round(Pango.FontDescription(font).get_size() / Pango.SCALE))


def with_font_size(font: str, size: int) -> str:
    description = Pango.FontDescription(font)
    description.set_size(size * Pango.SCALE)
    return description.to_string()


def font_without_size(font: str) -> str:
    """Just the typeface, since the size is shown on the slider instead."""
    description = Pango.FontDescription(font)
    description.unset_fields(Pango.FontMask.SIZE)
    return description.to_string()


def create_layout(text: str, font: str) -> Pango.Layout:
    layout = Pango.Layout.new(_FONT_MAP.create_context())
    layout.set_font_description(Pango.FontDescription(font))
    layout.set_text(text, -1)
    return layout


class TextBox:
    """Text being typed over the canvas, before it is rasterised into the image.

    Pango indexes text in UTF-8 bytes while the caret here counts characters, so
    the two are converted at the boundary rather than mixed up in the editing.
    """

    def __init__(self, x: float, y: float, color: Gdk.RGBA, font: str = DEFAULT_FONT):
        self._text = ""
        self._font = font
        self._layout: Pango.Layout | None = None
        self.color = color
        self.caret = 0
        self.x = 0.0
        self.y = 0.0
        self.move_to(x, y)

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, value: str) -> None:
        self._text = value
        self._layout = None

    @property
    def font(self) -> str:
        return self._font

    @font.setter
    def font(self, value: str) -> None:
        self._font = value
        self._layout = None

    @property
    def layout(self) -> Pango.Layout:
        if self._layout is None:
            self._layout = create_layout(self._text, self._font)
        return self._layout

    @property
    def size(self) -> tuple[int, int]:
        width, height = self.layout.get_pixel_size()
        return width, height

    def move_to(self, x: float, y: float) -> None:
        # Never past the top-left, for the same reason a paste cannot go there:
        # the canvas only ever grows right and down.
        self.x = max(0.0, x)
        self.y = max(0.0, y)

    def contains(self, x: float, y: float, padding: float = 0.0) -> bool:
        width, height = self.size
        return (
            self.x - padding <= x <= self.x + width + padding
            and self.y - padding <= y <= self.y + height + padding
        )

    # Editing

    def insert(self, text: str) -> None:
        self.text = self._text[: self.caret] + text + self._text[self.caret:]
        self.caret += len(text)

    def backspace(self) -> None:
        if self.caret == 0:
            return
        self.text = self._text[: self.caret - 1] + self._text[self.caret:]
        self.caret -= 1

    def delete(self) -> None:
        if self.caret >= len(self._text):
            return
        self.text = self._text[: self.caret] + self._text[self.caret + 1:]

    def move_caret(self, delta: int) -> None:
        self.caret = max(0, min(self.caret + delta, len(self._text)))

    def move_caret_line(self, delta: int) -> None:
        """Up or down a line, keeping roughly the same horizontal position."""
        layout = self.layout
        line_number, x_pos = layout.index_to_line_x(self._byte_index(), False)
        target = line_number + delta
        if not 0 <= target < layout.get_line_count():
            # Off the top or bottom: go where a text box usually goes.
            self.caret = 0 if delta < 0 else len(self._text)
            return
        _inside, index, trailing = layout.get_line_readonly(target).x_to_index(x_pos)
        self.caret = self._char_index(index, trailing)

    def move_caret_to_edge(self, end: bool) -> None:
        line = self._line()
        self.caret = self._char_index(line.start_index + (line.length if end else 0))

    def caret_at(self, x: float, y: float) -> None:
        """Put the caret nearest to a point in canvas coordinates."""
        _inside, index, trailing = self.layout.xy_to_index(
            round((x - self.x) * Pango.SCALE), round((y - self.y) * Pango.SCALE)
        )
        self.caret = self._char_index(index, trailing)

    def caret_rect(self) -> tuple[float, float, float]:
        """Where to draw the caret, in canvas coordinates."""
        strong, _weak = self.layout.get_cursor_pos(self._byte_index())
        return (
            self.x + strong.x / Pango.SCALE,
            self.y + strong.y / Pango.SCALE,
            strong.height / Pango.SCALE,
        )

    def _line(self) -> Pango.LayoutLine:
        line_number, _x = self.layout.index_to_line_x(self._byte_index(), False)
        return self.layout.get_line_readonly(line_number)

    def _byte_index(self) -> int:
        return len(self._text[: self.caret].encode())

    def _char_index(self, byte_index: int, trailing: int = 0) -> int:
        prefix = self._text.encode()[:byte_index].decode("utf-8", "ignore")
        return max(0, min(len(prefix) + trailing, len(self._text)))

    # Drawing

    def render(self, cr: cairo.Context, x: float | None = None, y: float | None = None) -> None:
        cr.save()
        cr.move_to(self.x if x is None else x, self.y if y is None else y)
        cr.set_source_rgba(self.color.red, self.color.green, self.color.blue, self.color.alpha)
        PangoCairo.show_layout(cr, self.layout)
        cr.restore()

    def render_surface(self) -> cairo.ImageSurface | None:
        """The typed text on its own transparent surface, ready to be stamped down."""
        width, height = self.size
        if not self._text or width <= 0 or height <= 0:
            return None
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        self.render(cairo.Context(surface), 0, 0)
        return surface
