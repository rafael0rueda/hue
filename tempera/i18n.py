# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

"""Translations.

Tempera ships in English only, but every string a person reads goes through
`_()`, so a translation can be added later without touching the code. The
strings are collected into `po/tempera.pot` by `meson compile tempera-pot`.

Strings with something filled in use `.format()` rather than an f-string, so
that the translator sees a whole sentence with named places in it.
"""

from __future__ import annotations

import gettext
import os

DOMAIN = "tempera"


def locale_dir() -> str | None:
    """Where the catalogues are: the installed prefix, or the system default."""
    return os.environ.get("TEMPERA_LOCALE_DIR") or None


_ = gettext.translation(DOMAIN, locale_dir(), fallback=True).gettext

__all__ = ["DOMAIN", "locale_dir", "_"]
