# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import os
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GdkPixbuf", "2.0")

from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

from . import APP_ID, APP_NAME, VERSION  # noqa: E402
from .file_io import load_document  # noqa: E402
from .window import HueWindow  # noqa: E402


def data_dir() -> Path | None:
    """Find the app's data directory, whether running from source or installed."""
    candidates = []
    if "HUE_DATA_DIR" in os.environ:
        candidates.append(Path(os.environ["HUE_DATA_DIR"]))
    candidates.append(Path(__file__).resolve().parent.parent / "data")
    candidates += [Path(d) / "hue" for d in GLib.get_system_data_dirs()]
    return next((path for path in candidates if path.is_dir()), None)


class HueApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_OPEN)

    def do_startup(self):
        Adw.Application.do_startup(self)
        self._load_resources()

        for name, callback in (("quit", self._on_quit), ("about", self._on_about)):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)

    def do_activate(self):
        window = self.props.active_window or HueWindow(self)
        window.present()

    def do_open(self, files, n_files, hint):
        try:
            document = load_document(files[0])
        except GLib.Error as error:
            print(f"hue: could not open image: {error.message}", file=sys.stderr)
            document = None
        HueWindow(self, document).present()

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
        window = self.props.active_window
        if window is not None:
            window.close()
        else:
            self.quit()

    def _on_about(self, *_):
        about = Adw.AboutDialog(
            application_name=APP_NAME,
            application_icon=APP_ID,
            version=VERSION,
            developer_name="Hue contributors",
            comments="A simple, offline raster paint app for the GNOME desktop.",
            license_type=Gtk.License.GPL_3_0,
        )
        about.present(self.props.active_window)


def main() -> int:
    return HueApplication().run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
