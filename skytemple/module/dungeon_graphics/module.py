#  Copyright 2020 Parakoopa
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
import logging
import sys
from typing import Union, List, Optional

from gi.repository import Gtk
from gi.repository.Gtk import TreeStore

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.error_handler import display_error
from skytemple.core.rom_project import RomProject
from skytemple.core.ui_utils import recursive_up_item_store_mark_as_modified, \
    recursive_generate_item_store_row_label
from skytemple.module.dungeon_graphics.controller.tileset import TilesetController
from skytemple.module.dungeon_graphics.controller.main import MainController, DUNGEON_GRAPHICS_NAME
from skytemple_files.common.types.file_types import FileType
from skytemple_files.container.dungeon_bin.model import DungeonBinPack
from skytemple_files.graphics.bg_list_dat.model import BgList
from skytemple_files.graphics.bma.model import Bma
from skytemple_files.graphics.bpa.model import Bpa
from skytemple_files.graphics.bpc.model import Bpc
from skytemple_files.graphics.bpl.model import Bpl

# TODO: Not so great that this is hard-coded, but how else can we really do it? - Maybe at least in the dungeondata.xml?
NUMBER_OF_TILESETS = 170
DUNGEON_BIN = 'DUNGEON/dungeon.bin'
logger = logging.getLogger(__name__)


class DungeonGraphicsModule(AbstractModule):
    @classmethod
    def depends_on(cls):
        return ['tiled_img']

    @classmethod
    def sort_order(cls):
        return 220

    def __init__(self, rom_project: RomProject):
        self.project = rom_project

        self.dungeon_bin: Optional[DungeonBinPack] = None
        self._tree_model = None
        self._tree_level_iter = []

    def load_tree_items(self, item_store: TreeStore, root_node):
        self.dungeon_bin: DungeonBinPack = self.project.open_file_in_rom(
            DUNGEON_BIN, FileType.DUNGEON_BIN, static_data=self.project.get_rom_module().get_static_data()
        )

        root = item_store.append(root_node, [
            'folder-pictures-symbolic', DUNGEON_GRAPHICS_NAME, self, MainController, 0, False, '', True
        ])
        self._tree_model = item_store
        self._tree_level_iter = []
        for i in range(0, NUMBER_OF_TILESETS):
            self._tree_level_iter.append(
                item_store.append(root, [
                    'image-x-generic-symbolic', f"Tileset {i}", self,  TilesetController, i, False, '', True
                ])
            )

        recursive_generate_item_store_row_label(self._tree_model[root])

    def mark_as_modified(self, item_id):
        # TODO
        pass
