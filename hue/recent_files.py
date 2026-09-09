# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from pathlib import Path

from gi.repository import Gio, GLib

MAX_RECENT = 8


def _recent_file_path() -> Path:
    directory = Path(GLib.get_user_config_dir()) / "hue"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "recent-files.txt"


def load_recent() -> list[str]:
    """URIs of recently opened/saved files, most recent first."""
    path = _recent_file_path()
    if not path.is_file():
        return []
    return [line for line in path.read_text().splitlines() if line]


def remember_recent(file: Gio.File) -> list[str]:
    """Move (or add) a file to the front of the recent list and persist it."""
    uri = file.get_uri()
    recent = ([uri] + [existing for existing in load_recent() if existing != uri])[:MAX_RECENT]
    _recent_file_path().write_text("\n".join(recent) + "\n")
    return recent


def forget_recent(uri: str) -> list[str]:
    """Drop a file that turned out to be missing or unreadable."""
    recent = [existing for existing in load_recent() if existing != uri]
    _recent_file_path().write_text("\n".join(recent) + "\n" if recent else "")
    return recent
