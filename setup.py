__version__ = '1.3.8'

import glob
import os
import pathlib
import subprocess
import sys

from setuptools import setup, find_packages

# README read-in
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()
# END README read-in


PO_FILES = 'data/locale/*/LC_MESSAGES/skytemple.po'


def create_mo_files():
    try:
        mo_files = []
        prefix = os.path.join(this_directory, 'skytemple')

        for po_path in glob.glob(str(pathlib.Path(prefix) / PO_FILES)):
            mo = pathlib.Path(po_path.replace('.po', '.mo'))

            subprocess.run(['msgfmt', '-o', str(mo), po_path], check=True)
            mo_files.append(str(mo.relative_to(prefix)))

        return mo_files
    except BaseException as ex:
        return []


def recursive_pkg_files(file_ext):
    directory = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'skytemple')
    paths = []
    for (path, directories, filenames) in os.walk(directory):
        for filename in filenames:
            if filename.endswith(file_ext):
                paths.append(os.path.relpath(os.path.join('..', path, filename), directory))
    return paths


def recursive_pkg_files_in(xpath):
    directory = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'skytemple', xpath)
    paths = []
    for (path, directories, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.relpath(os.path.join('..', path, filename), os.path.join(os.path.abspath(os.path.dirname(__file__)), 'skytemple')))
    return paths


setup(
    name='skytemple',
    version=__version__,
    packages=find_packages(),
    description='GUI Application to edit the ROM of Pokémon Mystery Dungeon Explorers of Sky (EU/US)',
    long_description=long_description,
    long_description_content_type='text/x-rst',
    url='https://github.com/SkyTemple/skytemple/',
    install_requires=[
        'ndspy >= 3.0.0',
        'skytemple-files >= 1.3.8',
        'skytemple-dtef >= 1.1.4',
        'skytemple-icons >= 1.3.2',
        'pygobject >= 3.26.0',
        'pycairo >= 1.16.0',
        'natsort >= 7.0.0',
        'tilequant >= 0.4.0',
        'skytemple-ssb-debugger >= 1.3.8.post2',
        'pygal >= 2.4.0',
        'CairoSVG >= 2.4.2',
        'gbulb >= 0.6.2',
        'psutil >= 5.8.0',
        'sentry-sdk >= 1.5'
        'packaging'
    ],
    extras_require={
        'discord':  ["pypresence >= 4.2.1"],
        'eventserver': ["skytemple-eventserver >= 1.0.0"]
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
    package_data={'skytemple': ['*.css'] + recursive_pkg_files('.glade') + recursive_pkg_files_in('data/') + create_mo_files()},
    entry_points='''
        [skytemple.module]
        rom=          skytemple.module.rom.module:RomModule
        bgp=          skytemple.module.bgp.module:BgpModule
        tiled_img=    skytemple.module.tiled_img.module:TiledImgModule
        map_bg=       skytemple.module.map_bg.module:MapBgModule
        script=       skytemple.module.script.module:ScriptModule
        gfxcrunch=    skytemple.module.gfxcrunch.module:GfxcrunchModule
        sprite=       skytemple.module.sprite.module:SpriteModule
        monster=      skytemple.module.monster.module:MonsterModule
        portrait=     skytemple.module.portrait.module:PortraitModule
        patch=        skytemple.module.patch.module:PatchModule
        lists=        skytemple.module.lists.module:ListsModule
        moves_items=  skytemple.module.moves_items.module:MovesItemsModule
        misc_graphics=skytemple.module.misc_graphics.module:MiscGraphicsModule
        dungeon=      skytemple.module.dungeon.module:DungeonModule
        dungeon_graphics=skytemple.module.dungeon_graphics.module:DungeonGraphicsModule
        strings      =skytemple.module.strings.module:StringsModule
        [console_scripts]
        skytemple=skytemple.main:main
    ''',
)
