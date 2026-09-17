# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

"""Interface preferences. Like the Recent Files list they are only a convenience,
so a config file that is missing, damaged or unwritable falls back to defaults."""

from __future__ import annotations

import configparser
import os
import shutil
from pathlib import Path

from gi.repository import GLib

PALETTE_POSITIONS = ("bottom", "left", "right")
DEFAULT_PALETTE_POSITION = "bottom"

CONFIG_NAME = "tempera"
# Tempera was called Hue before, and kept its settings under that name.
OLD_CONFIG_NAME = "hue"

_SECTION = "view"
_SHORTCUTS_SECTION = "shortcuts"


def config_dir() -> Path:
    return Path(GLib.get_user_config_dir()) / CONFIG_NAME


def migrate_old_config(root: Path | None = None) -> None:
    """Carry settings, shortcuts and recent files over from when the app was called Hue.

    It only happens while there is no Tempera directory yet, so it runs once and
    never overwrites anything; the old directory is left where it was.
    """
    root = Path(GLib.get_user_config_dir()) if root is None else root
    old, new = root / OLD_CONFIG_NAME, root / CONFIG_NAME
    if new.exists() or not old.is_dir():
        return
    temporary = root / (CONFIG_NAME + ".tmp")
    try:
        shutil.rmtree(temporary, ignore_errors=True)
        shutil.copytree(old, temporary)
        # Moved into place whole, so a failed copy is tried again next time.
        os.replace(temporary, new)
    except OSError:
        shutil.rmtree(temporary, ignore_errors=True)


def _settings_path() -> Path:
    return config_dir() / "settings.ini"


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


def load_setting(key: str, fallback: str = "") -> str:
    """One remembered preference, or the fallback when it was never saved."""
    return _load().get(_SECTION, key, fallback=fallback)


def save_settings(values: dict[str, str]) -> None:
    """Remember several preferences at once, leaving the others as they were."""
    parser = _load()
    if not parser.has_section(_SECTION):
        parser.add_section(_SECTION)
    for key, value in values.items():
        parser.set(_SECTION, key, str(value))
    _save(parser)


def load_palette_position() -> str:
    position = load_setting("palette-position", DEFAULT_PALETTE_POSITION)
    return position if position in PALETTE_POSITIONS else DEFAULT_PALETTE_POSITION


def save_palette_position(position: str) -> None:
    save_settings({"palette-position": position})


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
