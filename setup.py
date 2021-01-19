__version__ = '1.1.0'
import os

from setuptools import setup, find_packages

# README read-in
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()
# END README read-in


def recursive_pkg_files(file_ext):
    directory = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'skytemple')
    paths = []
    for (path, directories, filenames) in os.walk(directory):
        for filename in filenames:
            if filename.endswith(file_ext):
                paths.append(os.path.relpath(os.path.join('..', path, filename), directory))
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
        'skytemple-files >= 1.1.0',
        'skytemple-dtef >= 1.1.0',
        'skytemple-icons >= 0.1.0',
        'pygobject >= 3.26.0',
        'pycairo >= 1.16.0',
        'natsort >= 7.0.0',
        'tilequant >= 0.4.0',
        'skytemple-ssb-debugger >= 1.0.0',
        'pygal >= 2.4.0',
        'CairoSVG >= 2.4.2'
    ],
    extras_require={
        'discord':  ["pypresence >= 4.0.0"],
        'eventserver': ["skytemple-eventserver >= 1.0.0"]
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9'
    ],
    package_data={'skytemple': ['*.css', 'data/*/*/*/*/*', 'data/*', 'data/fixed_floor/*', 'data/back_illust/*'] + recursive_pkg_files('.glade')},
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
        misc_graphics=skytemple.module.misc_graphics.module:MiscGraphicsModule
        dungeon=      skytemple.module.dungeon.module:DungeonModule
        dungeon_graphics=skytemple.module.dungeon_graphics.module:DungeonGraphicsModule
        strings      =skytemple.module.strings.module:StringsModule
        [console_scripts]
        skytemple=skytemple.main:main
    ''',
)
