# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

"""The tests import straight from the source tree, so a module left out of the
install list only shows up as a crash in the installed app. Catch it here."""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "tempera"


def test_every_module_is_installed():
    installed = set(re.findall(r"'([\w/]+\.py)'", (PACKAGE / "meson.build").read_text()))
    modules = {path.relative_to(PACKAGE).as_posix() for path in PACKAGE.rglob("*.py")}
    assert modules - installed == set()


def test_every_icon_is_shipped_or_built_into_gtk():
    """Buttons must not depend on the desktop's icon theme.

    Under Flatpak the host theme is often out of reach (one in ~/.icons, say),
    and GTK then only has the few icons compiled into it, so anything else
    renders as a broken-image placeholder.
    """
    from gi.repository import Gio, Gtk

    Gtk.init()
    built_in = {
        name.removesuffix(".svg")
        for name in Gio.resources_enumerate_children("/org/gtk/libgtk/icons/", 0)
    }
    shipped = {
        path.name.removesuffix(".svg")
        for path in (PACKAGE.parent / "data" / "icons").rglob("*.svg")
    }
    used = set()
    for path in PACKAGE.rglob("*.py"):
        used |= set(re.findall(r'"([\w-]+-symbolic)"', path.read_text()))

    assert used, "the icon names were not found at all"
    assert used - shipped - built_in == set()


def test_nothing_is_still_called_hue():
    """The app was renamed from Hue; only the deliberate references to that remain."""
    allowed = {
        "tempera/settings.py": ['OLD_CONFIG_NAME = "hue"', "called Hue"],
        "data/io.github.rafael0rueda.Tempera.metainfo.xml": [
            "io.github.rafael0rueda.Hue",
            "called Hue",
            "Hue is now called Tempera",
            "carried over from Hue",
        ],
        "README.md": ["called Hue", "~/.config/hue/", "io.github.rafael0rueda.Hue/config/hue"],
        "tests/test_install.py": None,
        "tests/test_settings.py": ["old_hue_settings"],
    }
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split()
    leftovers = []
    for name in tracked:
        path = ROOT / name
        if name == "LICENSE" or path.suffix in {".png", ".svg"} or not path.is_file():
            continue
        if allowed.get(name, []) is None:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"hue", line, re.IGNORECASE) and not any(
                fragment in line for fragment in allowed.get(name, [])
            ):
                leftovers.append(f"{name}:{number}: {line.strip()}")
    assert leftovers == []


def test_the_desktop_file_opens_what_the_open_dialog_does():
    from tempera.file_io import OPEN_MIME_TYPES

    desktop = (ROOT / "data" / "io.github.rafael0rueda.Tempera.desktop").read_text(encoding="utf-8")
    line = next(line for line in desktop.splitlines() if line.startswith("MimeType="))
    assert set(filter(None, line.removeprefix("MimeType=").split(";"))) == set(OPEN_MIME_TYPES)


def test_version_matches_meson_and_the_newest_release_notes():
    from tempera import VERSION
    from tempera.main import metainfo_path, release_notes

    meson = (ROOT / "meson.build").read_text(encoding="utf-8")
    assert f"version: '{VERSION}'" in meson
    version, notes = release_notes(metainfo_path(ROOT / "data"))
    assert version == VERSION
    assert notes.startswith("<p>")


def test_release_notes_of_a_missing_or_broken_metainfo_are_none(tmp_path):
    from tempera.main import release_notes

    broken = tmp_path / "broken.xml"
    broken.write_text("<component>", encoding="utf-8")
    assert release_notes(None) is None
    assert release_notes(tmp_path / "missing.xml") is None
    assert release_notes(broken) is None
