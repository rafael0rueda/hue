# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

app_id = 'io.github.rafael0rueda.Tempera'

# Translated at build time: msgfmt fills in whatever po/ holds for the
# handful of keys and elements people actually read.
i18n.merge_file(
  input: app_id + '.desktop.in',
  output: app_id + '.desktop',
  type: 'desktop',
  po_dir: meson.project_source_root() / 'po',
  install: true,
  install_dir: datadir / 'applications',
)

i18n.merge_file(
  input: app_id + '.metainfo.xml.in',
  output: app_id + '.metainfo.xml',
  type: 'xml',
  po_dir: meson.project_source_root() / 'po',
  install: true,
  install_dir: datadir / 'metainfo',
)
install_data(
  'icons' / 'hicolor' / 'scalable' / 'apps' / app_id + '.svg',
  install_dir: datadir / 'icons' / 'hicolor' / 'scalable' / 'apps',
)

install_data('style.css', install_dir: pkgdatadir)
install_subdir('icons', install_dir: pkgdatadir)
