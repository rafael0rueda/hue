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
    'main.py',
    'text.py',
    'window.py',
  ),
  subdir: 'hue',
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
    'tools/text.py',
  ),
  subdir: 'hue/tools',
)

launcher = configuration_data()
launcher.set('PYTHON', python.full_path())
launcher.set('PYTHON_DIR', python.get_install_dir())
launcher.set('PKGDATADIR', pkgdatadir)

configure_file(
  input: 'hue.in',
  output: 'hue',
  configuration: launcher,
  install: true,
  install_dir: bindir,
  install_mode: 'rwxr-xr-x',
)
