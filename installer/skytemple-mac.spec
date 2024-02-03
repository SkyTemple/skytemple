# -*- mode: python ; coding: utf-8 -*-
import os
import sys
import shutil
from pathlib import PurePosixPath, Path
from PyInstaller.utils.hooks import collect_entry_point, copy_metadata

pkg_path = os.path.abspath(os.path.join("..", "skytemple"))
site_packages = next(p for p in sys.path if "site-packages" in p)

# The Homebrew lib path is different on ARM and Intel
homebrew_path = os.path.join(os.sep, "usr", "local")
if os.uname().machine == "arm64":
    homebrew_path = os.path.join(os.sep, "opt", "homebrew")

additional_datas = [
    (os.path.join(pkg_path, "data"), "data"),
    (os.path.join(pkg_path, "*.glade"), "."),
    (os.path.join(pkg_path, "*.css"), "."),
    # (os.path.join(site_packages, 'skytemple_rust*.so'), '.'),
    (
        os.path.join(site_packages, "skytemple_icons", "hicolor"),
        "skytemple_icons/hicolor",
    ),
    (
        os.path.join(site_packages, "skytemple_ssb_debugger", "data"),
        "skytemple_ssb_debugger/data",
    ),
    (
        os.path.join(site_packages, "skytemple_ssb_debugger", "*.glade"),
        "skytemple_ssb_debugger",
    ),
    (
        os.path.join(site_packages, "skytemple_ssb_debugger", "*.lang"),
        "skytemple_ssb_debugger",
    ),
    (
        os.path.join(site_packages, "skytemple_ssb_debugger", "controller", "*.glade"),
        "skytemple_ssb_debugger/controller",
    ),
    (
        os.path.join(
            site_packages,
            "skytemple_ssb_debugger",
            "controller",
            "desmume_control_ui",
            "*.glade",
        ),
        "skytemple_ssb_debugger/controller/desmume_control_ui",
    ),
    (
        os.path.join(site_packages, "skytemple_files", "_resources"),
        "skytemple_files/_resources",
    ),
    (
        os.path.join(
            site_packages, "skytemple_files", "graphics", "chara_wan", "Shadow.png"
        ),
        "skytemple_files/graphics/chara_wan",
    ),
    (os.path.join(site_packages, "skytemple_dtef", "template.png"), "skytemple_dtef"),
    (os.path.join(".", "armips"), "skytemple_files/_resources"),
    (os.path.join(site_packages, "cairocffi", "VERSION"), "cairocffi"),
    (os.path.join(site_packages, "cssselect2", "VERSION"), "cssselect2"),
    (os.path.join(site_packages, "tinycss2", "VERSION"), "tinycss2"),
    (os.path.join(site_packages, "cairosvg", "VERSION"), "cairosvg"),
    (os.path.join(site_packages, "gtkspellcheck", "_pylocales", "locales.db"), "."),
    (os.path.join(site_packages, "pygal", "css", "*"), "pygal/css"),
    (os.path.join(site_packages, "certifi", "cacert.pem"), "certifi"),
    # Themes
    ("Arc", "share/themes/Arc"),
    ("Arc-Dark", "share/themes/Arc-Dark"),
    ("ZorinBlue-Light", "share/themes/ZorinBlue-Light"),
    ("ZorinBlue-Dark", "share/themes/ZorinBlue-Dark"),
]

additional_binaries = [
    (os.path.join(site_packages, "desmume", "libdesmume.dylib"), "."),
    (
        os.path.join(homebrew_path, "lib", "libSDL-1.2.0.dylib"),
        ".",
    ),  # Must be installed with Homebrew
    (
        os.path.join(homebrew_path, "lib", "libSDL2-2.0.0.dylib"),
        ".",
    ),  # Must be installed with Homebrew
    (
        os.path.join(homebrew_path, "lib", "libenchant-2.dylib"),
        ".",
    ),  # Must be installed with Homebrew
    (
        os.path.join(homebrew_path, "lib", "libaspell.15.dylib"),
        ".",
    ),  # Gets installed with Enchant
    (
        os.path.join(
            homebrew_path, "lib", "enchant-2", "enchant_applespell.so"
        ),
        ".",
    ),  # Gets installed with Enchant
    (
        os.path.join(homebrew_path, "opt", "cairo", "lib", "libcairo.2.dylib"),
        ".",
    ),
    (os.path.join(site_packages, "libtilequant.dylib"), "."),
]

# Add all module *.glade files.
for path, directories, filenames in os.walk(os.path.join(pkg_path, "module")):
    for filename in filenames:
        if filename.endswith(".glade"):
            additional_datas.append(
                (
                    os.path.abspath(os.path.join("..", path, filename)),
                    f'skytemple/{str(PurePosixPath(Path(path.replace(pkg_path + "/", ""))))}',
                )
            )

block_cipher = None

# SkyTemple entrypoints
st_metadatas = copy_metadata("skytemple")
st_datas, st_hiddenimports = collect_entry_point("skytemple")


a = Analysis(
    ["../skytemple/main.py"],
    pathex=[os.path.abspath(os.path.join("..", "skytemple"))],
    binaries=additional_binaries,
    datas=additional_datas + st_datas + st_metadatas,
    hiddenimports=[
        "packaging.version",
        "packaging.specifiers",
        "packaging.requirements",
        "packaging.markers",
        "_sysconfigdata__win32_",
        "win32api",
        "certifi",
        "tilequant_dsoinfo",
        "skytemple.module.rom.module",
        "skytemple.module.bgp.module",
        "skytemple.module.tiled_img.module",
        "skytemple.module.map_bg.module",
        "skytemple.module.script.module",
        "skytemple.module.gfxcrunch.module",
        "skytemple.module.sprite.module",
        "skytemple.module.monster.module",
        "skytemple.module.portrait.module",
        "skytemple.module.patch.module",
        "skytemple.module.lists.module",
        "skytemple.module.moves_items.module",
        "skytemple.module.misc_graphics.module",
        "skytemple.module.music.module",
        "skytemple.module.dungeon.module",
        "skytemple.module.dungeon_graphics.module",
        "skytemple.module.strings.module",
        "skytemple.module.spritecollab.module",
    ]
    + st_hiddenimports,
    hookspath=[],
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
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="run_skytemple",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="skytemple",
)

app = BUNDLE(
    coll,
    name="SkyTemple.app",
    icon="skytemple.icns",
    version=os.getenv("PACKAGE_VERSION", "0.0.0"),
    bundle_identifier="de.parakoopa.skytemple",
)
