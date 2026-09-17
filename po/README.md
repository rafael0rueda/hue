<!-- SPDX-FileCopyrightText: 2026 Rafael Rueda -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# Translations

Tempera ships in English, but every string a person reads is marked for translation,
so a new language needs no changes to the code.

To add one, from a build directory (`meson setup builddir`):

```
meson compile -C builddir tempera-pot          # refresh po/tempera.pot
msginit -i po/tempera.pot -l de -o po/de.po    # start German, say
```

Then add `de` to `po/LINGUAS`, translate `po/de.po` in a text editor or a tool such as
Poedit, and `meson install` will compile and install it. `meson compile -C builddir
tempera-update-po` merges later string changes into the existing translations.
