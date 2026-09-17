# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

"""Interface preferences. Like the Recent Files list they are only a convenience,
so a config file that is missing, damaged or unwritable falls back to defaults."""

from __future__ import annotations

import configparser
import os
from pathlib import Path

from gi.repository import GLib

PALETTE_POSITIONS = ("bottom", "left", "right")
DEFAULT_PALETTE_POSITION = "bottom"

_SECTION = "view"
_SHORTCUTS_SECTION = "shortcuts"


def _settings_path() -> Path:
    return Path(GLib.get_user_config_dir()) / "hue" / "settings.ini"


def _load() -> configparser.ConfigParser:
    # Shortcut keys are action names such as "win.tool::pencil", so ":" cannot
    # be a delimiter, and they are case-sensitive.
    parser = configparser.ConfigParser(interpolation=None, delimiters=("=",))
    parser.optionxform = str
    try:
        parser.read_string(_settings_path().read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, configparser.Error):
        pass
    return parser


def load_palette_position() -> str:
    position = _load().get(_SECTION, "palette-position", fallback=DEFAULT_PALETTE_POSITION)
    return position if position in PALETTE_POSITIONS else DEFAULT_PALETTE_POSITION


def save_palette_position(position: str) -> None:
    parser = _load()
    if not parser.has_section(_SECTION):
        parser.add_section(_SECTION)
    parser.set(_SECTION, "palette-position", position)
    _save(parser)


def load_shortcut_overrides() -> dict[str, list[str]]:
    """Shortcuts changed from their defaults: action -> accelerators, [] for disabled."""
    parser = _load()
    if not parser.has_section(_SHORTCUTS_SECTION):
        return {}
    return {action: value.split() for action, value in parser.items(_SHORTCUTS_SECTION)}


def save_shortcut_overrides(overrides: dict[str, list[str]]) -> None:
    parser = _load()
    parser.remove_section(_SHORTCUTS_SECTION)
    if overrides:
        parser.add_section(_SHORTCUTS_SECTION)
        for action, accels in sorted(overrides.items()):
            parser.set(_SHORTCUTS_SECTION, action, " ".join(accels))
    _save(parser)


def _save(parser: configparser.ConfigParser) -> None:
    path = _settings_path()
    temporary = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with temporary.open("w", encoding="utf-8") as stream:
            parser.write(stream)
        # Replaced whole, so a crash mid-write cannot leave a truncated file.
        os.replace(temporary, path)
    except OSError:
        pass
