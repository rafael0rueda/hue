# Tempera

A straightforward raster paint application for Fedora / GNOME, in the spirit of the
classic Windows Paint. Built with GTK4 and libadwaita, it follows the system light/dark
preference and accent colour automatically, and works entirely offline.

![Tempera's main window: the tool palette on the left with the brush selected, a painted landscape with a house, a tree and the sun on the canvas, and the colour palette with recently picked colours, zoom level and canvas size along the bottom](data/screenshots/main-window.png)

## Installing a release

Each [release](https://github.com/rafael0rueda/tempera/releases) has a Flatpak bundle
attached. Download `Tempera-<version>-x86_64.flatpak` and install it for your user:

```
flatpak install --user Tempera-1.0.0-x86_64.flatpak
```

It runs on the GNOME 50 runtime, which Flatpak offers to fetch from Flathub if you do
not have it yet. Installing a newer bundle the same way updates it.

## Requirements

Fedora Workstation 40 or newer:

```
sudo dnf install python3-gobject python3-cairo gtk4 libadwaita
```

To build and install, also: `sudo dnf install meson ninja-build`

## Running from source

No build step is needed for development:

```
python3 -m tempera
```

Optionally pass an image to open: `python3 -m tempera picture.png`

## Running the tests

The pytest suite covers the drawing, file, clipboard, selection, text and undo logic,
and checks that every module and icon the app uses gets installed. The window tests
create real widgets, so run it inside your desktop session, or under `xvfb-run -a`
without one; no window ever appears.

```
sudo dnf install python3-pytest
python3 -m pytest
```

From a meson build directory, `meson test -C builddir` runs the same suite.

GitHub Actions runs the same suite on Fedora for every push and pull request,
validates the desktop entry and metainfo, and builds the Flatpak
([.github/workflows/ci.yml](.github/workflows/ci.yml)).

## Installing

```
meson setup builddir --prefix=/usr/local
meson install -C builddir
```

This installs the `tempera` launcher, the desktop entry, the app icon and the app data
(stylesheet plus tool icons). The launcher points at the installed data directory;
`TEMPERA_DATA_DIR` overrides it if you need to.

## Flatpak

`flatpak/io.github.rafael0rueda.Tempera.json` builds against `org.gnome.Platform` 50. It needs
`flatpak-builder` and the GNOME SDK, which are not installed by default:

```bash
sudo dnf install flatpak-builder
flatpak install flathub org.gnome.Sdk//50 org.gnome.Platform//50
flatpak-builder --user --install --force-clean build flatpak/io.github.rafael0rueda.Tempera.json
```

The manifest deliberately grants no network permission — the app has no reason to
reach the network, and the sandbox enforces that. It grants no filesystem access
either: Tempera only sees the images you pick in the Open and Save dialogs, drop onto the
canvas or copy from Files, all of which reach it through the desktop's file portal.

## Tools and shortcuts

| Tool          | Key | Notes                                                                |
| ------------- | --- | -------------------------------------------------------------------- |
| Pencil        | `P` | Hard-edged, no antialiasing                                          |
| Brush         | `B` | Soft round stroke                                                    |
| Airbrush      | `A` | Sprays dots across the brush size, and keeps spraying while held     |
| Eraser        | `E` | Paints the secondary (background) colour, or rubs back to nothing    |
| Shapes        |     | Nine shapes in one tool; see below                                   |
| Text          | `T` | Type onto the canvas in any installed font                           |
| Fill          | `F` | Flood fill, with a tolerance slider for how far it spreads           |
| Colour picker | `K` | Picks the colour under the cursor                                    |
| Select        | `S` | Rectangle to move, copy or cut                                       |
| Lasso select  | `Shift+S` | Any shape drawn by hand, to move, copy or cut                  |

The **Shapes** tool's options hold a grid of shapes, and each shape has its own key,
which also picks up the tool.

| Shape             | Key | How to draw it                                                   |
| ----------------- | --- | ---------------------------------------------------------------- |
| Line              | `L` | Drag; `Shift` snaps it to 45° steps                              |
| Curve             | `C` | Drag a line, then drag twice to bend it (`Enter` after one bend) |
| Arrow             | `W` | Drag from tail to tip; the head grows with the size              |
| Rectangle         | `R` | Drag; `Shift` draws a square                                     |
| Rounded rectangle | `U` | Drag; `Shift` draws a square                                     |
| Ellipse           | `O` | Drag; `Shift` draws a circle                                     |
| Triangle          | `I` | Drag; `Shift` makes it as wide as it is tall                     |
| Star              | `H` | Drag; `Shift` makes it regular                                   |
| Polygon           | `G` | Click each corner; click the first one again, or the last twice  |

**Fill shape** fills the closed shapes with the secondary colour, which the swatch
beside it shows; click the swatch to change it. The polygon and the
curve stay open for more clicks until they are finished: `Enter` lands one early, `Esc`
drops it, and picking another tool or shape lands it. Either way it is a single step
to undo.

Left click draws with the primary colour, right click with the secondary one. Both
colour swatches in the bottom bar work the same way: left click sets the primary
colour, right click the secondary. `X` swaps them.

Clicking either of the two large swatches opens the colour dialog, where a colour can
be typed in as a hex value and given an opacity: a see-through colour paints over what
is already there instead of replacing it. Colours picked lately gather in a second row
beside the fixed palette, so a mixed colour is one click away next time.

Each tool brings its own options under the size slider: the shapes and **Fill shape**
for the Shapes tool, **Density** for the airbrush, **Erase to nothing** for the eraser,
a tolerance for the fill, and the font for the text tool.

| Action                      | Shortcut                                         |
| --------------------------- | ------------------------------------------------ |
| New / Open / Save / Save As | `Ctrl+N` / `Ctrl+O` / `Ctrl+S` / `Ctrl+Shift+S`  |
| Print                       | `Ctrl+P`                                         |
| Canvas size                 | `Ctrl+E`                                         |
| Resize image                | `Ctrl+R`                                         |
| Select all                  | `Ctrl+A`                                         |
| Cut / Copy / Paste          | `Ctrl+X` / `Ctrl+C` / `Ctrl+V`                   |
| Nudge a selection or paste  | Arrow keys (`Shift` for 10 px)                   |
| Land / discard a paste      | `Enter` / `Esc`                                  |
| Drop / clear a selection    | `Esc` / `Delete`                                 |
| Land / discard typed text   | `Ctrl+Enter` / `Esc`                             |
| Undo / Redo                 | `Ctrl+Z` / `Ctrl+Shift+Z` (or `Ctrl+Y`)          |
| Zoom in / out / 100%        | `Ctrl++` / `Ctrl+-` / `Ctrl+0`, or `Ctrl`+scroll |
| Zoom to fit                 | `Ctrl+9`                                         |
| Show pixel grid             | `Ctrl+G`                                         |
| Smaller / bigger brush      | `[` / `]`                                        |
| Preferences                 | `Ctrl+,`                                         |
| Keyboard shortcuts          | `Ctrl+?`                                         |
| Quit                        | `Ctrl+Q`                                         |

### Customising shortcuts

The keys above are the defaults. **Keyboard Shortcuts** in the main menu (or `Ctrl+?`)
lists every shortcut: click one and press the new key, `Backspace` to remove it, or `Esc`
to leave it as it was. A key another action already uses can be moved over after a
confirmation. Crop, rotate and flip have no key by default but can be given one. Keys the
canvas needs — arrows, `Enter`, `Esc`, `Delete`, `Tab` — are listed but cannot be
reassigned. Changes are saved in `~/.config/tempera/settings.ini`; only keys that differ
from the defaults are stored, and **Reset All Shortcuts** puts everything back.

## Opening and saving

Images open in any format GdkPixbuf reads (PNG, JPEG, BMP, TIFF, WebP, GIF, ICO…), up
to 8192 × 8192 pixels; a larger image is refused with a message rather than loaded, as
is anything that is not an ordinary file, such as a named pipe. Reading and writing
happen in the background, with a spinner in the header bar, so a large image or a slow
disk never freezes the window; you can keep drawing while a save finishes, and the file
holds the image as it was when you asked to save it.
Photos open the right way up, following the orientation the camera or phone recorded.
**Recent Files** in the main menu lists the last eight images you opened or saved; one
that can no longer be opened is taken off the list when you pick it.

Saving writes PNG, JPEG, BMP, TIFF, WebP or ICO, picked by the file extension. A name
typed without one of those gets `.png` added — Tempera asks first if that would replace
an existing file. **Save As** to a JPEG asks for a quality from 1 to 100; `Ctrl+S`
afterwards keeps that choice without asking again, for as long as the window is open.
An image opened from a format Tempera cannot write, such as GIF, is never overwritten:
`Ctrl+S` asks where to save it, suggesting the same name as a PNG. The image is
written in full before it replaces the old file, so a save that fails, on a full disk
say, leaves the original untouched. BMP and JPEG have no transparency, so transparent
areas are saved as white; ICO files are limited to 256 × 256 pixels.

Closing a window, opening another image or starting a new one asks first when there are
unsaved changes, including a paste or typed text that has not landed yet; **Cancel**
leaves everything exactly as it was. `Ctrl+Q` closes every window, asking in each one
that has unsaved changes.

The title shows `•` while there are unsaved changes, and undoing back to the image as
it was last saved clears it again. Undo keeps up to 50 steps. Each step holds only the
part of the picture that edit changed, so brush strokes on a large photo cost little; a
step that changes the whole picture, such as a fill or a rotation, holds all of it, and
the history gives up its oldest steps rather than use more than 1 GB.

## Printing

**Print…** in the main menu (or `Ctrl+P`) first shows the page with the image on it.
**Fit to Page** makes the image as big as the paper allows, and **Actual Size** prints it
as big as it looks at 100% zoom, 96 pixels to the inch; an image too big for one page is
spread over several, which it says, to be laid side by side. The page turns to landscape
for a wide image, and **Portrait** and **Landscape** change that. **Print…** then opens
the system's print dialog, to choose the printer, paper and copies, or to print to a PDF.
What prints is the image as it was when you chose **Print…**, with any floating paste or
text landed first. Tempera remembers the fit, and the printer and paper last used.

## Zooming

`Ctrl`+scroll zooms around the pointer, so whatever is under it stays put; `Ctrl++` and
`Ctrl+-` step through the usual levels between 10% and 800%, and `Ctrl+0` — or clicking
the zoom level in the bottom bar — goes back to 100%. `Ctrl+9` fits the whole image in
the window, which is also how an image too large for the window opens. Drag with the
middle mouse button to move around a zoomed image, or pinch on a touchpad to zoom. The same three are in the main
menu, and scrolling over the zoom level in the bottom bar steps it up or down. Every tool keeps working at any zoom, and from 100% up each image pixel shows as
a crisp square, which makes pixel-level touch-ups with the pencil easy. The bottom bar
also shows which image pixel the pointer is over.

**Show Pixel Grid** in the main menu (or `Ctrl+G`) draws a thin line between every two
pixels from 400% zoom up; further out the lines would hide the picture. The grey lines
show on light and dark colours alike, though they are faint on mid grey. The grid is
only on screen and never saved into the image.

## What Tempera remembers

The window size, the tool and shape in hand, the brush and text sizes, the font, the fill
tolerance, the airbrush density, whether the pixel grid is on, both colours with the
ones picked lately, the JPEG quality, where the palette sits and the interface size
are all kept in `~/.config/tempera/settings.ini` and put back the next
time, along with how to fit a print. The printer and paper last printed on are kept in
`~/.config/tempera/print-settings.ini`. A **New image** can start transparent instead of white.

## Crash recovery

While an image has unsaved changes, Tempera keeps a copy of it every 30 seconds in its
own data folder. Your files are never touched — only **Save** writes them. If Tempera
stops without closing, because of a crash or a power cut, the next start asks about each
image left unsaved: **Recover** opens it as unsaved changes to the file it came from,
**Discard** throws the copy away, and **Decide Later** keeps it to ask again next time.
Saving, closing a window, or choosing **Discard** when closing deletes the copy, so it
only lasts as long as the unsaved work does. A recovered image starts a fresh undo
history.

## Moving the palette

The colour palette sits in the bottom bar by default. **Palette Position** in the main
menu moves it under the tools in the left sidebar, or to a column right of the canvas,
which leaves more height for the image on wide screens. The choice is remembered in
`~/.config/tempera/settings.ini`.

## Resizing the image

**Resize Image…** (`Ctrl+R`) in the main menu stretches or shrinks the whole picture, in
pixels or as a percentage. The height follows the width unless **Keep aspect ratio** is
turned off, and one `Ctrl+Z` puts the old size back. This is the picture itself; the
canvas around it is the next section.

## Resizing the canvas

Drag one of the three grips on the right, bottom and bottom-right edge of the image to
resize it by hand; the dashed outline and the size readout in the bottom bar follow the
pointer, and the change is applied when you let go. For an exact size, click that
readout or use **Canvas Size…** (`Ctrl+E`) in the main menu. Either way the image keeps
its top-left corner — growing the canvas adds white, shrinking it crops — and the
resize can be undone with `Ctrl+Z`.

While the select tool has a selection, its own eight handles take the place of these
grips; press `Esc` to drop the selection and get them back.

## Pasting images

`Ctrl+V` drops whatever image is on the clipboard — a screenshot, most usefully — onto
the canvas, where it floats inside a dashed outline until you decide where it goes.
Drag it into place, then press `Enter` or click anywhere outside it to stamp it down;
`Esc` or `Ctrl+Z` throws it away instead. Dragging an image file or an image from
another application onto the canvas does the same thing, and an image copied as a file
in Files pastes just as well as one copied as pixels.

If the pasted image runs off the right or bottom edge — a full-screen screenshot on a
smaller canvas usually does — the canvas grows to fit it when the paste lands, so
nothing is cropped. The one exception is the 8192 × 8192 pixel limit: whatever would
land past it is cut off, and a message says so. The size readout in the bottom bar counts out the size you are
heading for while the paste is still floating, and one `Ctrl+Z` afterwards takes back
both the pixels and the new canvas size.

`Ctrl+C` copies the whole canvas the other way, so it can be pasted into other
applications.

## Selecting, moving and copying

Pick the select tool (`S`) and drag a rectangle over the part of the image you want; a
dashed outline marks it out. Dragging from inside that outline lifts those pixels and
carries them somewhere else — hold `Ctrl` as you start the drag to leave a copy behind
instead of moving them. The pixels float exactly like a paste does, so `Enter` or a
click outside lands them, `Esc` or `Ctrl+Z` puts them back, and moving them past the
right or bottom edge grows the canvas. A move leaves white behind — the colour the
canvas is made of, not whichever colour you happen to be painting with — and the whole
move, the gap and the pixels in their new place, is a single `Ctrl+Z`.

Because a drag that starts inside the rectangle moves it, press `Esc` first when what
you want is to select a different area that overlaps the current one.

The lasso (`Shift+S`) selects any shape: hold the button down and draw around what you
want, and letting go closes the outline back to where it began. Everything above then
follows that outline rather than the rectangle around it: only the pixels inside it
move, copy, cut or clear, a move leaves a gap of the same shape, and the pixels copied
to the clipboard are transparent outside it. **Crop to Selection** keeps the rectangle
around the outline and makes what lies outside the outline transparent. The outline is
hard-edged, taking whole pixels, so nothing half-moved is left along its edge.

With the select tool or the lasso in hand, a selection has eight handles around it. Dragging one
stretches or squashes the selected pixels, again with `Ctrl` to leave the original in
place; the stretch keeps hard edges hard rather than blurring them. A floating paste
has the same handles, so a screenshot can be scaled down before it lands. The arrow
keys nudge a selection or a paste by one pixel, or ten with `Shift`, lifting the
selection the first time the same way a drag would.

`Ctrl+A` selects the whole image and switches to the select tool, and **Crop to
Selection** in the main menu cuts the canvas down to just the selected rectangle.

The selection outlives the tool that made it: `Ctrl+C` copies just that rectangle
rather than the whole canvas, `Ctrl+X` cuts it out and `Delete` clears it to white
without touching the clipboard, whichever tool is in hand. Only the select tool and the
lasso pick the pixels up, though — with a brush selected you paint over them as usual. `Esc`, or
a click outside the selection while the select tool or the lasso is in hand, drops it.

## Rotating and flipping

The main menu turns the whole image a quarter turn either way — swapping its width and
height — or mirrors it left to right or top to bottom. A paste or text still floating
is landed first and any selection is dropped; each is a single step to undo.

## Adding text

Pick the text tool (`T`) and click where the text should start: a dashed box appears
with a caret in it, and what you type is drawn straight onto the canvas in the primary
colour — right-click instead to type in the secondary one. The sidebar slider that
sizes the brush sizes the text instead while the text tool is selected, in points, and
**Font…** below it picks the family and style. Both apply to the box you are typing in
as well as the next one, so you can resize the text you are looking at.

The text stays editable until it lands. `Enter` starts a new line, the arrow keys,
`Home`, `End`, `Backspace` and `Delete` work as usual, and clicking inside the box puts
the caret where you clicked. Dragging the box moves it. Nothing is written into the
image until you press `Ctrl+Enter`, click outside the box, or switch to another tool;
`Esc` or `Ctrl+Z` throws it away instead.

Input methods work too: while one is still composing, say Japanese before it is
converted, the unfinished word shows underlined at the caret. Only what the input method
has finished lands in the image.

Once it lands the text is pixels like everything else — there is no going back to
editing it, only `Ctrl+Z`. Text that runs off the right or bottom edge grows the canvas
the same way a paste does. Because the image should look the same everywhere, the text
is laid out at 96 dpi regardless of the desktop's text scaling, so a size of 24 always
gives the same pixels.

## Keyboard and screen readers

Every tool, menu item and file action has a keyboard shortcut, and `Tab` moves through
the sidebar, the palette and the bottom bar. The colour swatches are buttons: `Tab` to
one and press `Enter` or `Space` to make it the primary colour, then `X` to swap the
primary and secondary colours around. With a pointer, right-clicking a swatch sets the
secondary colour directly.

Buttons that show only an icon carry a name for screen readers, the swatches announce
their colour by name ("Light blue (#99c1f1)"), and the canvas announces its size.

## Interface size

**Preferences** in the main menu (or `Ctrl+,`) has an **Interface Size** of 100%, 125%,
150% or 200%. It makes the whole app bigger at once: text, menus and dialogs, icons,
the tool buttons, the colour swatches, checkboxes and sliders, and the grips for
resizing the canvas. The change applies straight away to every open window and is
remembered. It adds to GNOME's own **Large Text** setting rather than replacing it; the
image itself and the file dialogs, which the desktop draws, keep their usual size. When
the window is too small for everything at a big size, the sidebar and palette scroll.

## Translations

Tempera is in English, but every string a person reads is marked for translation, and
the desktop entry and app metadata are translated at build time. [po/README.md](po/README.md)
explains how to add a language; no code has to change.

## Privacy

Tempera works entirely offline: no network, no update checks, no telemetry, no accounts.
The Flatpak has no network permission, so the sandbox enforces it.

Saved images carry no metadata — no EXIF, no camera details, no location — even when the
image you opened had them. The orientation an EXIF tag asked for is applied to the pixels
as the photo opens, so nothing is lost by dropping the rest.

The crash-recovery copies of unsaved images live in `~/.local/share/tempera/recovery/`
(`~/.var/app/io.github.rafael0rueda.Tempera/data/tempera/recovery/` for the Flatpak),
readable only by you, and are deleted as soon as the image is saved or its changes are
thrown away.

**Recent Files** keeps the last eight names in `~/.config/tempera/recent-files.txt`. It
follows GNOME's **Settings › Privacy › File History** switch: with that off, nothing is
recorded and the list stays empty. **Clear Recent Files** in the menu empties it at any
time.

[SECURITY.md](SECURITY.md) explains how to report a security problem.

## Theming

libadwaita does the work: the app follows the system colour scheme and accent colour
with no configuration. The only custom styling lives in `data/style.css`, written
against libadwaita's named colours (`@accent_bg_color`, `@headerbar_bg_color`, …) rather
than fixed values, so re-theming the app means editing that one file. Tool icons are
symbolic SVGs in `data/icons/`, so they recolour with the theme too.

## Licence

Tempera is free software under the GNU General Public License, version 3 or later; the
full text is in [LICENSE](LICENSE). Source and data files carry `SPDX-License-Identifier`
headers. The AppStream metainfo file is CC0-1.0, as AppStream requires of metadata.
