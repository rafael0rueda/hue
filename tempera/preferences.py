# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from collections.abc import Callable

from gi.repository import Adw, Gtk

from . import interface_size
from .i18n import _

# libadwaita's own width for this dialog, at the default interface size.
DIALOG_WIDTH = 640


def size_label(size: int) -> str:
    # Translators: an interface size, such as "150%".
    label = _("{size}%").format(size=size)
    if size == interface_size.DEFAULT_SIZE:
        # Translators: the interface size used unless another is chosen.
        return _("{size} (Default)").format(size=label)
    return label


class PreferencesDialog(Adw.PreferencesDialog):
    """Settings that apply to the whole app, rather than to one image."""

    def __init__(self, on_interface_size: Callable[[int], None]):
        super().__init__(title=_("Preferences"))
        self._on_interface_size = on_interface_size

        self.size_row = Adw.ComboRow(
            title=_("Interface Size"),
            subtitle=_("Makes text, buttons and icons bigger"),
            model=Gtk.StringList.new([size_label(size) for size in interface_size.SIZES]),
        )
        self.size_row.set_selected(interface_size.SIZES.index(interface_size.current()))
        self.size_row.connect("notify::selected", self._on_size_selected)

        group = Adw.PreferencesGroup(title=_("Accessibility"))
        group.add(self.size_row)
        page = Adw.PreferencesPage(title=_("General"))
        page.add(group)
        self.add(page)
        self._fit_to_size()

    def _fit_to_size(self) -> None:
        # Wider as the interface grows, so the rows keep their shape rather
        # than wrap their text into more lines than the dialog leaves room for.
        self.set_content_width(interface_size.scaled(DIALOG_WIDTH))

    def _on_size_selected(self, row: Adw.ComboRow, *_args) -> None:
        index = row.get_selected()
        if 0 <= index < len(interface_size.SIZES):
            self._on_interface_size(interface_size.SIZES[index])
            self._fit_to_size()
