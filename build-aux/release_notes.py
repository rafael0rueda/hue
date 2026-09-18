#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

"""Write the GitHub release page for one version, from the AppStream metainfo.

The metainfo already holds the release notes the About dialog and software
centres show, so the release page reuses them rather than keeping a second copy.

    build-aux/release_notes.py data/io.github.rafael0rueda.Tempera.metainfo.xml.in 1.0.0
"""

from __future__ import annotations

import sys
from pathlib import Path
from xml.etree import ElementTree

APP_ID = "io.github.rafael0rueda.Tempera"


def bundle_name(version: str) -> str:
    return f"Tempera-{version}-x86_64.flatpak"


def _text(element: ElementTree.Element) -> str:
    return " ".join("".join(element.itertext()).split())


def notes(metainfo: Path, version: str) -> str:
    """The description of that release as Markdown."""
    root = ElementTree.parse(metainfo).getroot()
    for release in root.iterfind("releases/release"):
        if release.get("version") == version:
            break
    else:
        raise LookupError(f"{metainfo} has no release {version}")
    blocks = []
    description = release.find("description")
    for child in [] if description is None else description:
        if child.tag == "p":
            blocks.append(_text(child))
        elif child.tag in ("ul", "ol"):
            marker = "-" if child.tag == "ul" else "1."
            blocks.append("\n".join(f"{marker} {_text(item)}" for item in child))
    return "\n\n".join(blocks)


def page(metainfo: Path, version: str) -> str:
    """The notes followed by how to install the bundle attached to the release."""
    bundle = bundle_name(version)
    return f"""{notes(metainfo, version)}

## Installing

Download **{bundle}** below and install it for your user:

```
flatpak install --user {bundle}
```

It runs on the GNOME 50 runtime, which Flatpak offers to fetch from Flathub if you do
not have it yet. Start Tempera from the app grid, or with `flatpak run {APP_ID}`.
"""


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    try:
        sys.stdout.write(page(Path(argv[1]), argv[2].removeprefix("v")))
    except (OSError, ElementTree.ParseError, LookupError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
