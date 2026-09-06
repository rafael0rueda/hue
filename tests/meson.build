# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

pytest = find_program('pytest', required: false)
if pytest.found()
  test(
    'pytest',
    pytest,
    args: [meson.project_source_root() / 'tests'],
    workdir: meson.project_source_root(),
  )
endif
