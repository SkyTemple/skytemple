"""Module that manages and loads modules"""
#  Copyright 2020-2021 Parakoopa and the SkyTemple Contributors
#
#  This file is part of SkyTemple.
#
#  SkyTemple is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SkyTemple is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SkyTemple.  If not, see <https://www.gnu.org/licenses/>.

import pkg_resources

MODULE_ENTRYPOINT_KEY = 'skytemple.module'


class Modules:
    _modules = {}

    @classmethod
    def load(cls):
        # Look up package entrypoints for modules
        cls._modules = {
            entry_point.name:
                entry_point.load() for entry_point in pkg_resources.iter_entry_points(MODULE_ENTRYPOINT_KEY)
        }
        if len(cls._modules) < 1:
            # PyInstaller under Windows has no idea what (custom) entrypoints are...
            # TODO: Figure out a better way to do this...
            cls._modules = cls._load_windows_modules()
        dependencies = {}
        for k, module in cls._modules.items():
            dependencies[k] = module.depends_on()
        resolved_deps = dep(dependencies)
        cls._modules = dict(sorted(cls._modules.items(), key=lambda x: resolved_deps.index(x[0])))
        for module in cls._modules.values():
            module.load()

    @classmethod
    def all(cls):
        """Returns a list of all loaded modules, ordered by dependencies"""
        return cls._modules

    @classmethod
    def _load_windows_modules(cls):
        from skytemple.module.rom.module import RomModule
        from skytemple.module.bgp.module import BgpModule
        from skytemple.module.tiled_img.module import TiledImgModule
        from skytemple.module.map_bg.module import MapBgModule
        from skytemple.module.script.module import ScriptModule
        from skytemple.module.monster.module import MonsterModule
        from skytemple.module.portrait.module import PortraitModule
        from skytemple.module.patch.module import PatchModule
        from skytemple.module.lists.module import ListsModule
        from skytemple.module.misc_graphics.module import MiscGraphicsModule
        from skytemple.module.dungeon.module import DungeonModule
        from skytemple.module.dungeon_graphics.module import DungeonGraphicsModule
        from skytemple.module.strings.module import StringsModule
        from skytemple.module.gfxcrunch.module import GfxcrunchModule
        from skytemple.module.sprite.module import SpriteModule
        from skytemple.module.moves_items.module import MovesItemsModule
        return {
            "rom": RomModule,
            "bgp": BgpModule,
            "tiled_img": TiledImgModule,
            "map_bg": MapBgModule,
            "script": ScriptModule,
            "monster": MonsterModule,
            "portrait": PortraitModule,
            "patch": PatchModule,
            "lists": ListsModule,
            "misc_graphics": MiscGraphicsModule,
            "dungeon": DungeonModule,
            "dungeon_graphics": DungeonGraphicsModule,
            "strings": StringsModule,
            "gfxcrunch": GfxcrunchModule,
            "sprite": SpriteModule,
            'moves_items': MovesItemsModule
        }


def dep(arg):
    """
    Dependency resolver

    "arg" is a dependency dictionary in which
    the values are the dependencies of their respective keys.

    Source: http://code.activestate.com/recipes/576570-dependency-resolver/

    Copyright: Louis RIVIERE
    Original license: MIT
    """
    d = dict((k, set(arg[k])) for k in arg)
    r = []
    while d:
        # values not in keys (items without dep)
        t = set(i for v in d.values() for i in v)-set(d.keys())
        # and keys without value (items without dep)
        t.update(k for k, v in d.items() if not v)
        # can be done right away
        r.append(t)
        # and cleaned up
        d = dict(((k, v-t) for k, v in d.items() if v))
    return [item for s in r for item in s]
