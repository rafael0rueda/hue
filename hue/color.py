# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from gi.repository import Gdk, GObject, Gtk

PALETTE = [
    "#000000", "#7a7a7a", "#c01c28", "#e66100", "#f5c211", "#33d17a",
    "#2ec27e", "#3584e4", "#1c71d8", "#9141ac", "#986a44", "#63452c",
    "#ffffff", "#deddda", "#f66151", "#ffbe6f", "#f9f06b", "#8ff0a4",
    "#99c1f1", "#dc8add",
]


def rgba(spec: str) -> Gdk.RGBA:
    color = Gdk.RGBA()
    color.parse(spec)
    return color


class ColorState(GObject.Object):
    """The primary (left click) and secondary (right click) colors."""

    __gsignals__ = {"changed": (GObject.SignalFlags.RUN_FIRST, None, ())}

    def __init__(self):
        super().__init__()
        self._primary = rgba("#000000")
        self._secondary = rgba("#ffffff")

    @property
    def primary(self) -> Gdk.RGBA:
        return self._primary

    @primary.setter
    def primary(self, value: Gdk.RGBA) -> None:
        self._primary = value
        self.emit("changed")

    @property
    def secondary(self) -> Gdk.RGBA:
        return self._secondary

    @secondary.setter
    def secondary(self, value: Gdk.RGBA) -> None:
        self._secondary = value
        self.emit("changed")

    def for_button(self, button: int) -> Gdk.RGBA:
        return self._secondary if button == Gdk.BUTTON_SECONDARY else self._primary

    def swap(self) -> None:
        self._primary, self._secondary = self._secondary, self._primary
        self.emit("changed")


class Swatch(Gtk.DrawingArea):
    """A clickable color square. Left click sets primary, right click secondary."""

    __gsignals__ = {"picked": (GObject.SignalFlags.RUN_FIRST, None, (int,))}

    def __init__(self, color: Gdk.RGBA, size: int = 22):
        super().__init__()
        self._color = color
        self.set_content_width(size)
        self.set_content_height(size)
        self.set_draw_func(self._draw)
        self.add_css_class("hue-swatch")

        click = Gtk.GestureClick(button=0)
        click.connect("pressed", self._on_pressed)
        self.add_controller(click)

    @property
    def color(self) -> Gdk.RGBA:
        return self._color

    @color.setter
    def color(self, value: Gdk.RGBA) -> None:
        self._color = value
        self.queue_draw()

    def _on_pressed(self, gesture, n_press, x, y):
        self.emit("picked", gesture.get_current_button())

    def _draw(self, area, cr, width, height, *_):
        radius = 4
        cr.new_sub_path()
        cr.arc(width - radius, radius, radius, -1.5708, 0)
        cr.arc(width - radius, height - radius, radius, 0, 1.5708)
        cr.arc(radius, height - radius, radius, 1.5708, 3.1416)
        cr.arc(radius, radius, radius, 3.1416, 4.7124)
        cr.close_path()

        cr.set_source_rgba(self._color.red, self._color.green, self._color.blue, self._color.alpha)
        cr.fill_preserve()

        outline = self.get_color()
        cr.set_source_rgba(outline.red, outline.green, outline.blue, 0.25)
        cr.set_line_width(1)
        cr.stroke()


class ColorBar(Gtk.Box):
    """Current colors, the fixed palette, and a custom color picker."""

    def __init__(self, colors: ColorState):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.colors = colors
        self.set_margin_top(6)
        self.set_margin_bottom(6)
        self.set_margin_start(12)
        self.set_margin_end(12)

        self._primary_swatch = Swatch(colors.primary, size=32)
        self._secondary_swatch = Swatch(colors.secondary, size=32)
        self._primary_swatch.set_tooltip_text("Primary color — click to change")
        self._secondary_swatch.set_tooltip_text("Secondary color — click to change")
        self._primary_swatch.connect("picked", lambda *_: self._choose(primary=True))
        self._secondary_swatch.connect("picked", lambda *_: self._choose(primary=False))

        current = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        current.append(self._primary_swatch)
        current.append(self._secondary_swatch)
        self.append(current)

        swap = Gtk.Button(icon_name="object-flip-horizontal-symbolic", tooltip_text="Swap colors (X)")
        swap.add_css_class("flat")
        swap.set_valign(Gtk.Align.CENTER)
        swap.connect("clicked", lambda *_: colors.swap())
        self.append(swap)

        grid = Gtk.Grid(row_spacing=4, column_spacing=4, valign=Gtk.Align.CENTER)
        for index, spec in enumerate(PALETTE):
            swatch = Swatch(rgba(spec))
            swatch.set_tooltip_text(spec)
            swatch.connect("picked", self._on_palette_picked)
            grid.attach(swatch, index % 10, index // 10, 1, 1)
        self.append(grid)

        colors.connect("changed", self._sync)

    def _on_palette_picked(self, swatch: Swatch, button: int) -> None:
        if button == Gdk.BUTTON_SECONDARY:
            self.colors.secondary = swatch.color
        else:
            self.colors.primary = swatch.color

    def _sync(self, *_):
        self._primary_swatch.color = self.colors.primary
        self._secondary_swatch.color = self.colors.secondary

    def _choose(self, primary: bool) -> None:
        dialog = Gtk.ColorDialog(with_alpha=False)
        initial = self.colors.primary if primary else self.colors.secondary

        def on_done(source, result):
            try:
                color = source.choose_rgba_finish(result)
            except Exception:
                return
            if color is None:
                return
            if primary:
                self.colors.primary = color
            else:
                self.colors.secondary = color

        dialog.choose_rgba(self.get_root(), initial, None, on_done)
