# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

"""The tests import straight from the source tree, so a module left out of the
install list only shows up as a crash in the installed app. Catch it here."""

import re
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent / "hue"


def test_every_module_is_installed():
    installed = set(re.findall(r"'([\w/]+\.py)'", (PACKAGE / "meson.build").read_text()))
    modules = {path.relative_to(PACKAGE).as_posix() for path in PACKAGE.rglob("*.py")}
    assert modules - installed == set()
