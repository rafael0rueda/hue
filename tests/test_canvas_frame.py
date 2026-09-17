# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Gtk

from tempera.canvas import Canvas, CanvasFrame
from tempera.color import ColorState
from tempera.document import Document


def make_frame() -> CanvasFrame:
    return CanvasFrame(Canvas(Document(), ColorState()))


def canvas_size(frame: CanvasFrame) -> tuple[int, int]:
    _, width, _, _ = frame.canvas.measure(Gtk.Orientation.HORIZONTAL, -1)
    _, height, _, _ = frame.canvas.measure(Gtk.Orientation.VERTICAL, -1)
    return width, height


def test_canvas_is_centred_when_there_is_room():
    frame = make_frame()
    width, height = canvas_size(frame)
    frame.do_size_allocate(width + 400, height + 200, -1)
    assert frame.offset == (200, 100)


def test_canvas_stays_top_left_when_it_does_not_fit():
    frame = make_frame()
    width, height = canvas_size(frame)
    frame.do_size_allocate(width - 100, height - 100, -1)
    assert frame.offset == (0, 0)


def test_offset_holds_while_dragging_and_catches_up_after():
    frame = make_frame()
    width, height = canvas_size(frame)
    frame.do_size_allocate(width + 400, height + 200, -1)

    frame.canvas._drag_origin = (0.0, 0.0)
    frame.do_size_allocate(width + 800, height + 800, -1)
    assert frame.offset == (200, 100)
    # The frame asks for room to grow from the pinned offset.
    _, natural, _, _ = frame.do_measure(Gtk.Orientation.HORIZONTAL, -1)
    assert natural == width + 200

    frame.canvas._drag_origin = None
    frame.do_size_allocate(width + 800, height + 800, -1)
    assert frame.offset == (400, 400)
