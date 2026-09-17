# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Gdk

from tempera.color import MAX_RECENT_COLORS, ColorState, rgba


def test_defaults_are_black_on_white():
    colors = ColorState()
    assert (colors.primary.red, colors.primary.green, colors.primary.blue) == (0, 0, 0)
    assert (colors.secondary.red, colors.secondary.green, colors.secondary.blue) == (1, 1, 1)


def test_setting_primary_emits_changed():
    colors = ColorState()
    seen = []
    colors.connect("changed", lambda *_args: seen.append(True))
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


# recently used colors


def test_picking_a_color_remembers_it():
    colors = ColorState()
    colors.primary = rgba("#ff0000")
    colors.secondary = rgba("#00ff00")
    assert [color.to_string() for color in colors.recent] == [
        rgba("#00ff00").to_string(),
        rgba("#ff0000").to_string(),
    ]


def test_picking_the_same_color_again_moves_it_to_the_front():
    colors = ColorState()
    colors.primary = rgba("#ff0000")
    colors.primary = rgba("#0000ff")
    colors.primary = rgba("#ff0000")
    assert len(colors.recent) == 2
    assert colors.recent[0].to_string() == rgba("#ff0000").to_string()


def test_only_so_many_colors_are_kept():
    colors = ColorState()
    for step in range(MAX_RECENT_COLORS + 5):
        colors.primary = rgba("#%02x0000" % step)
    assert len(colors.recent) == MAX_RECENT_COLORS


def test_swapping_does_not_add_to_the_recent_colors():
    colors = ColorState()
    colors.swap()
    assert colors.recent == []
