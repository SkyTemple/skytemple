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
    (os.path.join(site_packages, "cairocffi", "VERSION"), "cairocffi"),
    #(os.path.join(site_packages, "cssselect2", "VERSION"), "cssselect2"),
    #(os.path.join(site_packages, "tinycss2", "VERSION"), "tinycss2"),
    (os.path.join(site_packages, "cairosvg", "VERSION"), "cairosvg"),
    (os.path.join(site_packages, "pylocales", "locales.db"), "."),
    (os.path.join(site_packages, "pygal", "css", "*"), 'pygal/css'),
    (os.path.join("D:/", "a", "_temp", "msys", "msys64", "mingw64", "share", "hunspell", "*"), 'share/hunspell'),

    # These aren't auto dectected for some reason :(
    (os.path.join("D:/", "a", "_temp", "msys", "msys64", "mingw64", 'share', 'fontconfig'), 'share/fontconfig'),
    (os.path.join("D:/", "a", "_temp", "msys", "msys64", "mingw64", 'share', 'glib-2.0'), 'share/glib-2.0'),
    (os.path.join("D:/", "a", "_temp", "msys", "msys64", "mingw64", 'share', 'gtksourceview-3.0'), 'share/gtksourceview-3.0'),
    (os.path.join("D:/", "a", "_temp", "msys", "msys64", "mingw64", 'share', 'icons'), 'share/icons'),
    (os.path.join("D:/", "a", "_temp", "msys", "msys64", "mingw64", 'share', 'locale'), 'share/locale'),
    (os.path.join("D:/", "a", "_temp", "msys", "msys64", "mingw64", 'share', 'themes'), 'share/themes'),

    # Themes
    ('Arc', 'share/themes/Arc'),
    ('Arc-Dark', 'share/themes/Arc-Dark')
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
    (os.path.join(site_packages, "desmume", "SDL.dll"), "."),
    (os.path.join(site_packages, "skytemple_tilequant", "aikku", "libtilequant.dll"), "skytemple_tilequant/aikku"),
    (os.path.join("D:/", "a", "_temp", "msys", "msys64", "mingw64", "bin", "libenchant-2.dll"), 'enchant/data/mingw64/bin'),
    (os.path.join("D:/", "a", "_temp", "msys", "msys64", "mingw64", "bin", "libglib-2.0-0.dll"), 'enchant/data/mingw64/bin'),
    (os.path.join("D:/", "a", "_temp", "msys", "msys64", "mingw64", "bin", "libgmodule-2.0-0.dll"), 'enchant/data/mingw64/bin'),
    (os.path.join("D:/", "a", "_temp", "msys", "msys64", "mingw64", "lib", "enchant-2", "enchant_hunspell.dll"), 'lib/enchant-2'),
    (os.path.join("D:/", "a", "_temp", "msys", "msys64", "mingw64", "bin", "libhunspell-1.7-0.dll"), '.'),
    (os.path.join("D:/", "a", "_temp", "msys", "msys64", "mingw64", "bin", "libcrypto-1_1-x64.dll"), '.'),
    (os.path.join("D:/", "a", "_temp", "msys", "msys64", "mingw64", "bin", "libssl-1_1-x64.dll"), '.'),
]

block_cipher = None


a = Analysis(['../skytemple/main.py'],
             pathex=[os.path.abspath(os.path.join('..', 'skytemple'))],
             binaries=additional_binaries,
             datas=additional_datas,
             hiddenimports=['pkg_resources.py2_warn', 'packaging.version', 'packaging.specifiers',
                            'packaging.requirements', 'packaging.markers', '_sysconfigdata__win32_', 'win32api'],
             hookspath=[os.path.abspath(os.path.join('.', 'hooks'))],
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
          debug=False,
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
