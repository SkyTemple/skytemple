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
import os
import sys
import webbrowser
from shutil import which
from typing import Tuple, List

from gi.repository.Gtk import TreeStore

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.rom_project import RomProject
from skytemple.core.ui_utils import data_dir
from skytemple.module.gfxcrunch.controller.gfxcrunch import GfxcrunchController

GFXCRUNCH_BIN = 'ppmd_gfxcrunch.exe'
WINE_BIN = 'wine'
ENABLE_GFXCRUNCH = True


class GfxcrunchModule(AbstractModule):
    @classmethod
    def depends_on(cls):
        return []

    @classmethod
    def sort_order(cls):
        return 0  # n/a

    def __init__(self, rom_project: RomProject):
        pass

    def load_tree_items(self, item_store: TreeStore, root_node):
        pass   # n/a

    def is_available(self):
        if not ENABLE_GFXCRUNCH:
            return False

        path = os.path.join(data_dir(), GFXCRUNCH_BIN)
        if not os.path.exists(path):
            return False

        if not sys.platform.startswith('win'):
            if which(WINE_BIN) is None:
                return False

        return True

    def get_gfxcrunch_cmd(self) -> Tuple[str, List[str], bool]:
        """Returns the CMD for gfxcrunch and the base argument list and if shell=True"""
        if sys.platform.startswith('win'):
            return os.path.join(data_dir(), GFXCRUNCH_BIN), [], False
        return WINE_BIN, [os.path.join(data_dir(), GFXCRUNCH_BIN)], False

    def import_sprite(self, dir_fn: str) -> bytes:
        return GfxcrunchController(self).import_sprite(dir_fn)

    def export_sprite(self, wan: bytes, dir_fn: str):
        return GfxcrunchController(self).export_sprite(wan, dir_fn)

    def open_gfxcrunch_page(self):
        webbrowser.open_new_tab('https://projectpokemon.org/home/forums/topic/31407-pokemon-mystery-dungeon-2-psy_commandos-tools-and-research-notes/')
