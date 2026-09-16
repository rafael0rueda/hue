# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Recent Files list. It is only a convenience, so a config directory that
cannot be read or written leaves it empty rather than breaking open or save."""

from __future__ import annotations

import os
from pathlib import Path

from gi.repository import Gio, GLib

MAX_RECENT = 8


def _recent_file_path() -> Path:
    return Path(GLib.get_user_config_dir()) / "hue" / "recent-files.txt"


def load_recent() -> list[str]:
    """URIs of recently opened/saved files, most recent first."""
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
    uri = file.get_uri()
    recent = ([uri] + [existing for existing in load_recent() if existing != uri])[:MAX_RECENT]
    _save_recent(recent)
    return recent


def forget_recent(uri: str) -> list[str]:
    """Drop a file that turned out to be missing or unreadable."""
    recent = [existing for existing in load_recent() if existing != uri]
    _save_recent(recent)
    return recent
