<!-- SPDX-FileCopyrightText: 2026 Rafael Rueda -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# Security policy

## Reporting a problem

Please report security problems privately, through
[GitHub's private vulnerability reporting](https://github.com/rafael0rueda/tempera/security/advisories/new),
rather than in a public issue. Tempera is a spare-time project, so expect a first reply
within a couple of weeks.

Useful in a report: what you did, what happened, the file that caused it if there is one,
and the versions of Tempera, GTK and your distribution.

## What is supported

Fixes go into the newest release. There are no patch releases for older versions.

## What Tempera does to stay out of trouble

- **It never uses the network.** There is no update check, no telemetry and no accounts.
  The Flatpak has no network permission at all, so the sandbox enforces that.
- **It sees only the files you choose.** The Flatpak has no filesystem permission either:
  images reach it through the desktop's file portal, one file at a time.
- **Images are decoded by GdkPixbuf**, which is where an attack in a malicious image would
  land. Tempera refuses an image whose header claims more than 8192 × 8192 pixels before
  those pixels are decoded, refuses anything that is not an ordinary file (a named pipe or
  a device would otherwise never finish being read), and refuses files far larger than any
  real image. Keeping your system, or the Flatpak runtime, up to date is what keeps the
  decoders themselves current.
- **Saved images carry no metadata.** No EXIF, no location, no camera details, even when
  the image you opened had them.
- **Recent Files** is a list of file names in `~/.config/tempera/`. It follows GNOME's
  File History setting, and **Clear Recent Files** in the main menu empties it.
