# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

from hue.document import (
    MAX_UNDO,
    Document,
    copy_surface,
    crop_surface,
    new_surface,
)

from pixels import paint_pixel, pixel_at

RED = (1.0, 0.0, 0.0, 1.0)
WHITE = (1.0, 1.0, 1.0, 1.0)


# new_surface / crop_surface / copy_surface


def test_new_surface_fills_with_color():
    surface = new_surface(3, 3, RED)
    assert pixel_at(surface, 0, 0) == (255, 0, 0, 255)
    assert pixel_at(surface, 2, 2) == (255, 0, 0, 255)


def test_new_surface_defaults_to_opaque_white():
    surface = new_surface(2, 2)
    assert pixel_at(surface, 0, 0) == (255, 255, 255, 255)


def test_crop_surface_extracts_the_rectangle():
    source = new_surface(4, 4, WHITE)
    paint_pixel(source, 2, 1, RED)
    cropped = crop_surface(source, 1, 1, 2, 2)
    assert cropped.get_width() == 2
    assert cropped.get_height() == 2
    assert pixel_at(cropped, 1, 0) == (255, 0, 0, 255)
    assert pixel_at(cropped, 0, 0) == (255, 255, 255, 255)


def test_copy_surface_is_independent_of_the_source():
    source = new_surface(2, 2, WHITE)
    copy = copy_surface(source)
    paint_pixel(source, 0, 0, RED)
    assert pixel_at(copy, 0, 0) == (255, 255, 255, 255)


# Undo / redo


def test_undo_redo_round_trip():
    document = Document(new_surface(2, 2, WHITE))
    assert not document.can_undo
    assert not document.can_redo

    document.begin_change()
    paint_pixel(document.surface, 0, 0, RED)
    document.commit_change()

    assert document.can_undo
    assert not document.can_redo
    assert pixel_at(document.surface, 0, 0) == (255, 0, 0, 255)

    document.undo()
    assert pixel_at(document.surface, 0, 0) == (255, 255, 255, 255)
    assert not document.can_undo
    assert document.can_redo

    document.redo()
    assert pixel_at(document.surface, 0, 0) == (255, 0, 0, 255)
    assert document.can_undo
    assert not document.can_redo


def test_undo_with_nothing_to_undo_is_a_no_op():
    document = Document(new_surface(1, 1, WHITE))
    document.undo()
    assert pixel_at(document.surface, 0, 0) == (255, 255, 255, 255)


def test_commit_change_clears_the_redo_stack():
    document = Document(new_surface(1, 1, WHITE))
    document.begin_change()
    document.commit_change()
    document.undo()
    assert document.can_redo

    document.begin_change()
    document.commit_change()
    assert not document.can_redo


def test_undo_history_is_capped_at_max_undo():
    document = Document(new_surface(1, 1, WHITE))
    for _ in range(MAX_UNDO + 5):
        document.begin_change()
        document.commit_change()
    assert len(document._undo) == MAX_UNDO


# Resize


def test_resize_grow_keeps_existing_pixels_anchored_top_left():
    document = Document(new_surface(2, 2, RED))
    document.resize(4, 4)
    assert (document.width, document.height) == (4, 4)
    assert pixel_at(document.surface, 0, 0) == (255, 0, 0, 255)
    assert pixel_at(document.surface, 3, 3) == (255, 255, 255, 255)
    assert document.can_undo


def test_resize_crop_discards_pixels_outside_the_new_size():
    document = Document(new_surface(4, 4, RED))
    document.resize(1, 1)
    assert (document.width, document.height) == (1, 1)
    assert pixel_at(document.surface, 0, 0) == (255, 0, 0, 255)


def test_resize_to_the_same_size_is_a_no_op():
    document = Document(new_surface(2, 2, WHITE))
    document.resize(2, 2)
    assert not document.can_undo


# Erase


def test_erase_fills_the_rect_with_the_given_color():
    document = Document(new_surface(3, 3, RED))
    document.erase((1, 1, 1, 1))
    assert pixel_at(document.surface, 1, 1) == (255, 255, 255, 255)
    assert pixel_at(document.surface, 0, 0) == (255, 0, 0, 255)
    assert document.can_undo


# Paste


def test_paste_stamps_without_growing_when_it_fits():
    document = Document(new_surface(4, 4, WHITE))
    document.paste(new_surface(2, 2, RED), 0, 0)
    assert (document.width, document.height) == (4, 4)
    assert pixel_at(document.surface, 0, 0) == (255, 0, 0, 255)
    assert pixel_at(document.surface, 3, 3) == (255, 255, 255, 255)


def test_paste_grows_the_canvas_when_it_overhangs():
    document = Document(new_surface(2, 2, WHITE))
    document.paste(new_surface(2, 2, RED), 2, 2)
    assert (document.width, document.height) == (4, 4)
    assert pixel_at(document.surface, 2, 2) == (255, 0, 0, 255)
    # The room the growth added, outside the pasted rectangle, is left white.
    assert pixel_at(document.surface, 0, 2) == (255, 255, 255, 255)


def test_paste_erases_the_source_rect_it_moved_from():
    document = Document(new_surface(4, 4, RED))
    document.paste(new_surface(1, 1, RED), 3, 3, erase=(0, 0, 1, 1))
    assert pixel_at(document.surface, 0, 0) == (255, 255, 255, 255)
    assert pixel_at(document.surface, 3, 3) == (255, 0, 0, 255)


def test_paste_growth_and_erase_undo_in_a_single_step():
    document = Document(new_surface(2, 2, RED))
    document.paste(new_surface(1, 1, RED), 3, 3, erase=(0, 0, 1, 1))
    assert (document.width, document.height) == (4, 4)

    document.undo()
    assert (document.width, document.height) == (2, 2)
    assert pixel_at(document.surface, 0, 0) == (255, 0, 0, 255)
