# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

import resource
import struct
import zlib
from pathlib import Path

import pytest
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk

from hue.document import MAX_SIZE, Document, new_surface
from hue.file_io import (
    ICO_MAX_SIZE,
    format_for,
    image_filters,
    load_document,
    load_surface,
    save_document,
    with_default_extension,
)

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


# with_default_extension


def test_with_default_extension_adds_png_to_a_bare_name(tmp_path):
    file = with_default_extension(gio_file(tmp_path / "drawing"))
    assert file.get_path() == str(tmp_path / "drawing.png")


def test_with_default_extension_keeps_a_name_that_has_one(tmp_path):
    chosen = gio_file(tmp_path / "photo.jpg")
    assert with_default_extension(chosen).equal(chosen)


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


def write_png(path: Path, width: int, height: int) -> None:
    pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, width, height)
    pixbuf.fill(0xFFFFFFFF)
    pixbuf.savev(str(path), "png", [], [])


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def test_load_surface_accepts_the_largest_canvas_size(tmp_path):
    path = tmp_path / "wide.png"
    write_png(path, MAX_SIZE, 1)
    assert load_surface(gio_file(path)).get_width() == MAX_SIZE


def test_load_surface_refuses_an_image_wider_than_a_canvas_can_be(tmp_path):
    path = tmp_path / "too-wide.png"
    write_png(path, MAX_SIZE + 1, 1)
    with pytest.raises(GLib.Error, match=f"{MAX_SIZE + 1} × 1 px"):
        load_surface(gio_file(path))


def test_load_surface_refuses_a_decompression_bomb_without_decoding_it(tmp_path):
    # A few kilobytes of PNG declaring 60000 × 60000 pixels: about 14 GB decoded.
    side = 60000
    header = struct.pack(">IIBBBBB", side, side, 8, 6, 0, 0, 0)
    rows = zlib.compress(b"\0" * (side * 4 + 1) * 64, 9)
    path = tmp_path / "bomb.png"
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", header)
        + png_chunk(b"IDAT", rows)
        + png_chunk(b"IEND", b"")
    )

    peak_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    with pytest.raises(GLib.Error, match="60000 × 60000 px"):
        load_surface(gio_file(path))
    peak_growth_kib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss - peak_before
    assert peak_growth_kib < 256 * 1024


def test_load_surface_refuses_a_file_that_is_not_local():
    with pytest.raises(GLib.Error, match="not a file on this computer"):
        load_surface(Gio.File.new_for_uri("https://example.com/picture.png"))


def test_load_surface_raises_for_a_missing_file(tmp_path):
    with pytest.raises(GLib.Error):
        load_surface(gio_file(tmp_path / "missing.png"))


def test_load_surface_raises_for_a_file_that_is_not_an_image(tmp_path):
    path = tmp_path / "notes.png"
    path.write_text("not really a picture")
    with pytest.raises(GLib.Error):
        load_surface(gio_file(path))


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


def test_save_document_jpeg_quality_affects_file_size(tmp_path):
    document = Document(new_surface(64, 64, WHITE))
    for x in range(64):
        for y in range(64):
            paint_pixel(document.surface, x, y, RED if (x + y) % 2 else WHITE)

    low = tmp_path / "low.jpg"
    high = tmp_path / "high.jpg"
    save_document(document, gio_file(low), quality=10)
    save_document(document, gio_file(high), quality=95)

    assert low.stat().st_size < high.stat().st_size
    # Still a readable image at either quality.
    reloaded = load_document(gio_file(high))
    assert (reloaded.width, reloaded.height) == (64, 64)


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


def test_a_failed_save_leaves_the_existing_file_untouched(tmp_path):
    path = tmp_path / "icon.ico"
    path.write_bytes(b"the original icon")
    document = Document(new_surface(ICO_MAX_SIZE + 1, 16, WHITE))
    document.modified = True

    with pytest.raises(GLib.Error, match=f"at most {ICO_MAX_SIZE}"):
        save_document(document, gio_file(path))

    assert path.read_bytes() == b"the original icon"
    assert document.file is None
    assert document.modified is True


def test_save_document_raises_rather_than_crashing_for_a_missing_folder(tmp_path):
    with pytest.raises(GLib.Error):
        save_document(Document(new_surface(1, 1, WHITE)), gio_file(tmp_path / "gone" / "out.png"))


def test_save_document_writes_through_a_symlink(tmp_path):
    target = tmp_path / "real.png"
    write_png(target, 1, 1)
    link = tmp_path / "link.png"
    link.symlink_to(target)
    document = Document(new_surface(3, 2, WHITE))

    save_document(document, gio_file(link))

    assert link.is_symlink()
    reloaded = load_document(gio_file(target))
    assert (reloaded.width, reloaded.height) == (3, 2)
