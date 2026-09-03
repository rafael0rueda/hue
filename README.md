# Hue

A straightforward raster paint application for Fedora / GNOME, in the spirit of the
classic Windows Paint. Built with GTK4 and libadwaita, it follows the system light/dark
preference and accent colour automatically, and works entirely offline.

## Requirements

Fedora Workstation 40 or newer:

```
sudo dnf install python3-gobject python3-cairo gtk4 libadwaita
```

To build and install, also: `sudo dnf install meson ninja-build`

## Running from source

No build step is needed for development:

```
python3 -m hue
```

Optionally pass an image to open: `python3 -m hue picture.png`

## Installing

```
meson setup builddir --prefix=/usr/local
meson install -C builddir
```

This installs the `hue` launcher, the desktop entry, the app icon and the app data
(stylesheet plus tool icons). The launcher points at the installed data directory;
`HUE_DATA_DIR` overrides it if you need to.

## Flatpak

`flatpak/io.github.rafa.Hue.json` builds against `org.gnome.Platform` 50. It needs
`flatpak-builder` and the GNOME SDK, which are not installed by default:

```bash
sudo dnf install flatpak-builder
flatpak install flathub org.gnome.Sdk//50 org.gnome.Platform//50
flatpak-builder --user --install --force-clean build flatpak/io.github.rafa.Hue.json
```

The manifest deliberately grants no network permission — the app has no reason to
reach the network, and the sandbox enforces that.

## Tools and shortcuts

| Tool          | Key | Notes                                        |
| ------------- | --- | -------------------------------------------- |
| Pencil        | `P` | Hard-edged, no antialiasing                  |
| Brush         | `B` | Soft round stroke                            |
| Eraser        | `E` | Paints the secondary (background) colour     |
| Line          | `L` |                                              |
| Rectangle     | `R` | "Fill shape" fills with the secondary colour |
| Ellipse       | `O` |                                              |
| Fill          | `F` | Flood fill with a small colour tolerance     |
| Colour picker | `K` | Picks the colour under the cursor            |

Left click draws with the primary colour, right click with the secondary one. Both
colour swatches in the bottom bar work the same way: left click sets the primary
colour, right click the secondary. `X` swaps them.

| Action                      | Shortcut                                        |
| --------------------------- | ----------------------------------------------- |
| New / Open / Save / Save As | `Ctrl+N` / `Ctrl+O` / `Ctrl+S` / `Ctrl+Shift+S` |
| Undo / Redo                 | `Ctrl+Z` / `Ctrl+Shift+Z` (or `Ctrl+Y`)         |
| Quit                        | `Ctrl+Q`                                        |

Images open in any format GdkPixbuf reads (PNG, JPEG, BMP, TIFF, WebP…) and are saved
in the format matching the file extension, defaulting to PNG.

## Theming

libadwaita does the work: the app follows the system colour scheme and accent colour
with no configuration. The only custom styling lives in `data/style.css`, written
against libadwaita's named colours (`@accent_bg_color`, `@sidebar_bg_color`, …) rather
than fixed values, so re-theming the app means editing that one file. Tool icons are
symbolic SVGs in `data/icons/`, so they recolour with the theme too.

## Before publishing

The application ID `io.github.rafa.Hue` is a placeholder. Rename it (in `data/`,
`flatpak/` and `hue/__init__.py`) and add a `<url type="homepage">` to the metainfo
file before submitting anywhere.
