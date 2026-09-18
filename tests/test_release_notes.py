# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

import importlib.util
from fnmatch import fnmatch
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
METAINFO = ROOT / "data" / "io.github.rafael0rueda.Tempera.metainfo.xml.in"
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"

_spec = importlib.util.spec_from_file_location(
    "release_notes", ROOT / "build-aux" / "release_notes.py"
)
release_notes = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(release_notes)


def test_notes_turn_paragraphs_and_lists_into_markdown():
    notes = release_notes.notes(METAINFO, "0.5.0")
    assert notes.startswith("Fixes and improvements:\n\n- Photos open the right way up")
    assert "\n\nPrivacy and accessibility:\n\n- Recent Files follows" in notes
    # Lines wrapped in the XML come out as one line each.
    assert all(not line.startswith(" ") for line in notes.splitlines())


def test_the_page_says_how_to_install_the_attached_bundle():
    page = release_notes.page(METAINFO, "0.5.0")
    assert "flatpak install --user Tempera-0.5.0-x86_64.flatpak" in page


def test_an_unknown_version_is_an_error():
    with pytest.raises(LookupError):
        release_notes.notes(METAINFO, "9.9.9")
    assert release_notes.main(["release_notes.py", str(METAINFO), "v9.9.9"]) == 1


def test_the_workflow_attaches_the_bundle_the_notes_name():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert 'mv tempera.flatpak "Tempera-$version-x86_64.flatpak"' in workflow
    assert fnmatch(release_notes.bundle_name("1.2.3"), "Tempera-*-x86_64.flatpak")
    assert "files: Tempera-*-x86_64.flatpak" in workflow


def test_the_workflow_builds_the_manifest_that_exists():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "manifest-path: flatpak/io.github.rafael0rueda.Tempera.json" in workflow
    assert (ROOT / "flatpak" / "io.github.rafael0rueda.Tempera.json").is_file()
