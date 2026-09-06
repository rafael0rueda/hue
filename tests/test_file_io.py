# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

from pathlib import Path

from gi.repository import Gdk, GdkPixbuf, Gio, Gtk

from hue.document import Document, new_surface
from hue.file_io import format_for, image_filters, load_document, save_document

from pixels import paint_pixel, pixel_at

RED = (1.0, 0.0, 0.0, 1.0)
WHITE = (1.0, 1.0, 1.0, 1.0)
TRANSPARENT = (0.0, 0.0, 0.0, 0.0)


def gio_file(path: Path) -> Gio.File:
    return Gio.File.new_for_path(str(path))


# format_for


def test_format_for_known_extensions():
    assert format_for(gio_file(Path("a.png"))) == "png"
    assert format_for(gio_file(Path("a.jpg"))) == "jpeg"
    assert format_for(gio_file(Path("a.jpeg"))) == "jpeg"
    assert format_for(gio_file(Path("a.bmp"))) == "bmp"
    assert format_for(gio_file(Path("a.tiff"))) == "tiff"
    assert format_for(gio_file(Path("a.tif"))) == "tiff"
    assert format_for(gio_file(Path("a.webp"))) == "webp"
    assert format_for(gio_file(Path("a.ico"))) == "ico"


def test_format_for_is_case_insensitive():
    assert format_for(gio_file(Path("a.PNG"))) == "png"
    assert format_for(gio_file(Path("a.JPG"))) == "jpeg"


def test_format_for_defaults_to_png_for_unknown_or_missing_extension():
    assert format_for(gio_file(Path("a.xyz"))) == "png"
    assert format_for(gio_file(Path("a"))) == "png"


# image_filters


def test_image_filters_offers_images_png_and_all_files():
    store = image_filters()
    names = [store.get_item(i).get_name() for i in range(store.get_n_items())]
    assert names == ["Images", "PNG image", "All files"]
    assert all(isinstance(store.get_item(i), Gtk.FileFilter) for i in range(store.get_n_items()))


# load_document


def test_load_document_reads_pixels_and_sets_the_file(tmp_path):
    path = tmp_path / "loaded.png"
    pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 2, 2)
    pixbuf.fill(0x00FF00FF)  # opaque green, RGBA byte order
    pixbuf.savev(str(path), "png", [], [])

    file = gio_file(path)
    document = load_document(file)

    assert (document.width, document.height) == (2, 2)
    assert pixel_at(document.surface, 0, 0) == (0, 255, 0, 255)
    assert document.file == file


# save_document


def test_save_and_load_png_round_trips_alpha(tmp_path):
    document = Document(new_surface(2, 2, WHITE))
    paint_pixel(document.surface, 1, 0, RED)
    paint_pixel(document.surface, 0, 1, TRANSPARENT)

    file = gio_file(tmp_path / "out.png")
    save_document(document, file)

    reloaded = load_document(file)
    assert pixel_at(reloaded.surface, 0, 0) == (255, 255, 255, 255)
    assert pixel_at(reloaded.surface, 1, 0) == (255, 0, 0, 255)
    assert pixel_at(reloaded.surface, 0, 1) == (0, 0, 0, 0)


def test_save_document_updates_document_state(tmp_path):
    document = Document(new_surface(1, 1, WHITE))
    document.modified = True
    seen = []
    document.connect("state-changed", lambda *_: seen.append(True))

    file = gio_file(tmp_path / "out.png")
    save_document(document, file)

    assert document.file == file
    assert document.modified is False
    assert seen == [True]


def test_save_document_flattens_transparency_onto_white_for_bmp(tmp_path):
    document = Document(new_surface(2, 1, WHITE))
    paint_pixel(document.surface, 0, 0, TRANSPARENT)
    paint_pixel(document.surface, 1, 0, RED)

    file = gio_file(tmp_path / "out.bmp")
    save_document(document, file)

    reloaded = load_document(file)
    # BMP has no alpha channel: the transparent pixel composites onto white,
    # and the opaque one round-trips losslessly.
    assert pixel_at(reloaded.surface, 0, 0) == (255, 255, 255, 255)
    assert pixel_at(reloaded.surface, 1, 0) == (255, 0, 0, 255)
