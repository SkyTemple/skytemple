from setuptools import setup, find_packages

# README read-in
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()
# END README read-in

setup(
    name='skytemple',
    version='0.0.1',
    packages=find_packages(),
    description='GUI Application to edit the ROM of Pokémon Mystery Dungeon Explorers of Sky (EU/US)',
    long_description=long_description,
    long_description_content_type='text/x-rst',
    url='https://github.com/Parakoopa/skytemple/',
    install_requires=[
        # TODO
    ],
    classifiers=[
        # TODO
    ],
    entry_points='''
        [skytemple.module]
        map_bg=       skytemple.module.map_bg.module:MapBgModule
        tiled_bg=     skytemple.module.tiled_bg.module:TiledBgModule
    ''',
    #bgp=          skytemple.module.bgp.module:BgpModule
    #dungeon=      skytemple.module.dungeon.module:DungeonModule
    #item=         skytemple.module.item.module:ItemModule
    #music=        skytemple.module.music.module:MusicModule
    #portrait=     skytemple.module.portrait.module:PortraitModule
    #script=       skytemple.module.script.module:ScriptModule
    #sprite=       skytemple.module.sprite.module:SpriteModule
    #stats=        skytemple.module.stats.module:StatsModule
    #strings=      skytemple.module.strings.module:StringsModule
)
