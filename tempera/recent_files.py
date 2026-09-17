# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Recent Files list. It is only a convenience, so a config directory that
cannot be read or written leaves it empty rather than breaking open or save."""

from __future__ import annotations

import os
from pathlib import Path

from gi.repository import Gio

from .settings import config_dir

MAX_RECENT = 8
# GNOME's own switch for this, in Settings › Privacy › File History.
PRIVACY_SCHEMA = "org.gnome.desktop.privacy"
REMEMBER_KEY = "remember-recent-files"


def _recent_file_path() -> Path:
    return config_dir() / "recent-files.txt"


def remembering_allowed() -> bool:
    """Whether the desktop wants file history kept at all.

    Nothing is recorded or shown while GNOME's File History switch is off. The
    schema is missing on other desktops, where the answer is simply yes.
    """
    source = Gio.SettingsSchemaSource.get_default()
    schema = None if source is None else source.lookup(PRIVACY_SCHEMA, True)
    if schema is None or not schema.has_key(REMEMBER_KEY):
        return True
    return Gio.Settings.new(PRIVACY_SCHEMA).get_boolean(REMEMBER_KEY)


def load_recent() -> list[str]:
    """URIs of recently opened/saved files, most recent first."""
    if not remembering_allowed():
        return []
    try:
        text = _recent_file_path().read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    return [line for line in text.splitlines() if line][:MAX_RECENT]


def _save_recent(recent: list[str]) -> None:
    path = _recent_file_path()
    temporary = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text("".join(uri + "\n" for uri in recent), encoding="utf-8")
        # Replaced whole, so a crash mid-write cannot leave half a list.
        os.replace(temporary, path)
    except OSError:
        pass


def remember_recent(file: Gio.File) -> list[str]:
    """Move (or add) a file to the front of the recent list and persist it."""
    if not remembering_allowed():
        return []
    uri = file.get_uri()
    recent = ([uri] + [existing for existing in load_recent() if existing != uri])[:MAX_RECENT]
    _save_recent(recent)
    return recent


def forget_recent(uri: str) -> list[str]:
    """Drop a file that turned out to be missing or unreadable."""
    recent = [existing for existing in load_recent() if existing != uri]
    _save_recent(recent)
    return recent


def clear_recent() -> list[str]:
    """Forget every remembered file, for someone who would rather not keep the list."""
    try:
        _recent_file_path().unlink(missing_ok=True)
    except OSError:
        pass
    return []
