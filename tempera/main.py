# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GdkPixbuf", "2.0")

from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

from . import APP_ID, APP_NAME, VERSION  # noqa: E402
from .file_io import load_document  # noqa: E402
from .recent_files import remember_recent  # noqa: E402
from .settings import migrate_old_config  # noqa: E402
from .window import TemperaWindow  # noqa: E402


WEBSITE = "https://github.com/rafael0rueda/tempera"
ISSUES = WEBSITE + "/issues"


def metainfo_path(directory: Path | None = None) -> Path | None:
    """The AppStream metainfo, next to the data in a source tree or in share/metainfo installed."""
    directory = data_dir() if directory is None else directory
    if directory is None:
        return None
    name = f"{APP_ID}.metainfo.xml"
    for candidate in (directory / name, directory.parent / "metainfo" / name):
        if candidate.is_file():
            return candidate
    return None


def release_notes(path: Path | None) -> tuple[str, str] | None:
    """(version, notes) for the newest release in the metainfo, for the About dialog.

    The notes are the release's description, which is already the small subset
    of markup (paragraphs and lists) the dialog understands.
    """
    if path is None:
        return None
    try:
        release = ElementTree.parse(path).getroot().find("releases/release")
    except (OSError, ElementTree.ParseError):
        return None
    if release is None:
        return None
    description = release.find("description")
    notes = "" if description is None else "".join(
        ElementTree.tostring(child, encoding="unicode") for child in description
    )
    return release.get("version", ""), notes


def data_dir() -> Path | None:
    """Find the app's data directory, whether running from source or installed."""
    candidates = []
    if "TEMPERA_DATA_DIR" in os.environ:
        candidates.append(Path(os.environ["TEMPERA_DATA_DIR"]))
    candidates.append(Path(__file__).resolve().parent.parent / "data")
    candidates += [Path(d) / "tempera" for d in GLib.get_system_data_dirs()]
    return next((path for path in candidates if path.is_dir()), None)


class TemperaApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_OPEN)

    def do_startup(self):
        Adw.Application.do_startup(self)
        migrate_old_config()
        self._load_resources()

        for name, callback in (("quit", self._on_quit), ("about", self._on_about)):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)

    def do_activate(self):
        window = self.props.active_window or TemperaWindow(self)
        window.present()

    def do_open(self, files, n_files, hint):
        error_message = None
        try:
            document = load_document(files[0])
        except GLib.Error as error:
            error_message = error.message
            document = None
        else:
            remember_recent(files[0])
        window = TemperaWindow(self, document)
        window.present()
        if error_message is not None:
            print(f"tempera: could not open image: {error_message}", file=sys.stderr)
            window.show_toast(f"Could not open image: {error_message}")

    def _load_resources(self) -> None:
        directory = data_dir()
        if directory is None:
            return

        display = Gdk.Display.get_default()
        if display is None:
            return

        icons = directory / "icons"
        if icons.is_dir():
            Gtk.IconTheme.get_for_display(display).add_search_path(str(icons))

        stylesheet = directory / "style.css"
        if stylesheet.is_file():
            provider = Gtk.CssProvider()
            provider.load_from_string(stylesheet.read_text())
            Gtk.StyleContext.add_provider_for_display(
                display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

    def _on_quit(self, *_):
        # Each window asks about its own unsaved changes; the application ends
        # once the last one has gone.
        windows = self.get_windows()
        if not windows:
            self.quit()
        for window in windows:
            window.close()

    def _on_about(self, *_):
        about = Adw.AboutDialog(
            application_name=APP_NAME,
            application_icon=APP_ID,
            version=VERSION,
            developer_name="Rafael Rueda",
            copyright="© 2026 Rafael Rueda",
            comments="A simple, offline raster paint app for the GNOME desktop.",
            website=WEBSITE,
            issue_url=ISSUES,
            license_type=Gtk.License.GPL_3_0,
        )
        notes = release_notes(metainfo_path())
        if notes is not None and notes[0] == VERSION:
            about.set_release_notes_version(notes[0])
            about.set_release_notes(notes[1])
        about.present(self.props.active_window)


def main() -> int:
    return TemperaApplication().run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
