# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import PurePosixPath, Path

pkg_path = os.path.abspath(os.path.join('..', 'skytemple'))
site_packages = next(p for p in sys.path if 'site-packages' in p)

additional_files = []
additional_datas = [
    (os.path.join(pkg_path, 'data'), 'data'),
    (os.path.join(pkg_path, '*.glade'), '.'),
    (os.path.join(pkg_path, '*.css'), '.'),
    (os.path.join(site_packages, 'skytemple_rust*.pyd'), '.'),
    (os.path.join(site_packages, 'skytemple_icons', 'hicolor'), 'skytemple_icons/hicolor'),
    (os.path.join(site_packages, 'skytemple_ssb_debugger', 'data'), 'skytemple_ssb_debugger/data'),
    (os.path.join(site_packages, 'skytemple_ssb_debugger', '*.glade'), 'skytemple_ssb_debugger'),
    (os.path.join(site_packages, 'skytemple_ssb_debugger', '*.lang'), 'skytemple_ssb_debugger'),
    (os.path.join(site_packages, 'skytemple_ssb_debugger', 'controller', '*.glade'), 'skytemple_ssb_debugger/controller'),
    (os.path.join(site_packages, 'skytemple_files', '_resources'), 'skytemple_files/_resources'),
    (os.path.join(site_packages, 'skytemple_files', 'graphics', 'chara_wan', 'Shadow.png'), 'skytemple_files/graphics/chara_wan'),
    (os.path.join(site_packages, 'skytemple_dtef', 'template.png'), 'skytemple_dtef'),
    (os.path.join('.', 'armips.exe'), 'skytemple_files/_resources'),
    (os.path.join(site_packages, 'desmume', 'frontend', 'control_ui', '*.glade'), 'desmume/frontend/control_ui'),
    (os.path.join(site_packages, "gtkspellcheck", "_pylocales", "locales.db"), "."),
    (os.path.join(site_packages, "pygal", "css", "*"), 'pygal/css'),
    (os.path.join(site_packages, 'certifi', 'cacert.pem'), 'certifi'),

    # Themes
    ('Arc', 'share/themes/Arc'),
    ('Arc-Dark', 'share/themes/Arc-Dark'),
    ('ZorinBlue-Light', 'share/themes/ZorinBlue-Light'),
    ('ZorinBlue-Dark', 'share/themes/ZorinBlue-Dark'),
]
# Add all module *.glade files.
paths = []
for (path, directories, filenames) in os.walk(os.path.join(pkg_path, 'module')):
    for filename in filenames:
        if filename.endswith('.glade'):
            additional_datas.append((os.path.abspath(os.path.join('..', path, filename)),
                                     f'skytemple/{str(PurePosixPath(Path(path.replace(pkg_path + "/", ""))))}'))

additional_binaries = [
    (os.path.join(site_packages, "desmume", "libdesmume.dll"), "."),
    (os.path.join(site_packages, "desmume", "SDL2.dll"), "."),
    (os.path.join(site_packages, "skytemple_tilequant", "aikku", "libtilequant.dll"), "skytemple_tilequant/aikku"),
]

block_cipher = None


a = Analysis([os.path.join('..', 'skytemple', 'main.py')],
             pathex=[os.path.abspath(os.path.join('..', 'skytemple'))],
             binaries=additional_binaries,
             datas=additional_datas,
             hiddenimports=['pkg_resources.py2_warn', 'packaging.version', 'packaging.specifiers',
                            'packaging.requirements', 'packaging.markers', '_sysconfigdata__win32_', 'win32api',
                            'certifi'],
             hookspath=[os.path.abspath(os.path.join('.', 'hooks'))],
             hooksconfig={
                 "gi": {
                     "module-versions": {
                         "Gtk": "3.0",
                         "GtkSource": "4",
                     },
                 },
             },
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data,
          cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='skytemple',
          debug=True,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True,
          icon=os.path.abspath(os.path.join('.', 'skytemple.ico')))

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               additional_files,
               strip=False,
               upx=True,
               upx_exclude=[],
               version=os.getenv('PACKAGE_VERSION', '0.0.0'),
               name='skytemple')
