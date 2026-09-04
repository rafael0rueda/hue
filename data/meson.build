app_id = 'io.github.rafael0rueda.Hue'

install_data(app_id + '.desktop', install_dir: datadir / 'applications')
install_data(app_id + '.metainfo.xml', install_dir: datadir / 'metainfo')
install_data(
  'icons' / 'hicolor' / 'scalable' / 'apps' / app_id + '.svg',
  install_dir: datadir / 'icons' / 'hicolor' / 'scalable' / 'apps',
)

install_data('style.css', install_dir: pkgdatadir)
install_subdir('icons', install_dir: pkgdatadir)
