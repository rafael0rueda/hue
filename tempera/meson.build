# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

python.install_sources(
  files(
    '__init__.py',
    '__main__.py',
    'canvas.py',
    'clipboard.py',
    'color.py',
    'document.py',
    'file_io.py',
    'i18n.py',
    'interface_size.py',
    'main.py',
    'preferences.py',
    'recent_files.py',
    'settings.py',
    'shortcuts.py',
    'shortcuts_dialog.py',
    'text.py',
    'window.py',
  ),
  subdir: 'tempera',
)

python.install_sources(
  files(
    'tools/__init__.py',
    'tools/base.py',
    'tools/brush.py',
    'tools/ellipse.py',
    'tools/eraser.py',
    'tools/fill.py',
    'tools/line.py',
    'tools/pencil.py',
    'tools/picker.py',
    'tools/rectangle.py',
    'tools/select.py',
    'tools/text.py',
  ),
  subdir: 'tempera/tools',
)

launcher = configuration_data()
launcher.set('PYTHON', python.full_path())
launcher.set('PYTHON_DIR', python.get_install_dir())
launcher.set('PKGDATADIR', pkgdatadir)
launcher.set('LOCALEDIR', localedir)

configure_file(
  input: 'tempera.in',
  output: 'tempera',
  configuration: launcher,
  install: true,
  install_dir: bindir,
  install_mode: 'rwxr-xr-x',
)
