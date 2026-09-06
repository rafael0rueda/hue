# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Gdk

from hue.color import ColorState, rgba


def test_defaults_are_black_on_white():
    colors = ColorState()
    assert (colors.primary.red, colors.primary.green, colors.primary.blue) == (0, 0, 0)
    assert (colors.secondary.red, colors.secondary.green, colors.secondary.blue) == (1, 1, 1)


def test_setting_primary_emits_changed():
    colors = ColorState()
    seen = []
    colors.connect("changed", lambda *_: seen.append(True))
    colors.primary = rgba("#ff0000")
    assert seen == [True]
    assert colors.primary.red == 1


def test_swap_exchanges_primary_and_secondary():
    colors = ColorState()
    primary, secondary = colors.primary, colors.secondary
    colors.swap()
    assert colors.primary == secondary
    assert colors.secondary == primary


def test_for_button_picks_secondary_only_for_the_secondary_button():
    colors = ColorState()
    assert colors.for_button(Gdk.BUTTON_PRIMARY) == colors.primary
    assert colors.for_button(Gdk.BUTTON_SECONDARY) == colors.secondary
