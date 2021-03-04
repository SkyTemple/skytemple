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
import logging
from typing import Optional

from gi.repository import Gtk
from gi.repository.Gtk import TreeStore

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.open_request import OpenRequest, REQUEST_TYPE_DUNGEON_TILESET
from skytemple.core.rom_project import RomProject
from skytemple.core.ui_utils import recursive_up_item_store_mark_as_modified, \
    recursive_generate_item_store_row_label
from skytemple.module.dungeon_graphics.controller.dungeon_bg import DungeonBgController
from skytemple.module.dungeon_graphics.controller.colvec import ColvecController
from skytemple.module.dungeon_graphics.controller.tileset import TilesetController
from skytemple.module.dungeon_graphics.controller.main import MainController, DUNGEON_GRAPHICS_NAME
from skytemple_files.common.types.file_types import FileType
from skytemple_files.container.dungeon_bin.model import DungeonBinPack
from skytemple_files.graphics.dbg.model import Dbg
from skytemple_files.graphics.dma.model import Dma
from skytemple_files.graphics.dpc.model import Dpc
from skytemple_files.graphics.dpci.model import Dpci
from skytemple_files.graphics.dpl.model import Dpl
from skytemple_files.graphics.dpla.model import Dpla
from skytemple_files.graphics.colvec.model import Colvec
from skytemple_files.common.i18n_util import f, _

# TODO: Not so great that this is hard-coded, but how else can we really do it? - Maybe at least in the dungeondata.xml?
NUMBER_OF_TILESETS = 170
NUMBER_OF_BACKGROUNDS = 29
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
        self._colvec_pos = None

    def load_tree_items(self, item_store: TreeStore, root_node):
        self.dungeon_bin: DungeonBinPack = self.project.open_file_in_rom(
            DUNGEON_BIN, FileType.DUNGEON_BIN, static_data=self.project.get_rom_module().get_static_data()
        )

        root = item_store.append(root_node, [
            'skytemple-e-dungeon-tileset-symbolic', DUNGEON_GRAPHICS_NAME, self, MainController, 0, False, '', True
        ])
        self._tree_model = item_store
        self._tree_level_iter = []
        for i in range(0, NUMBER_OF_TILESETS):
            self._tree_level_iter.append(
                item_store.append(root, [
                    'skytemple-e-dungeon-tileset-symbolic', f"{_('Tileset')} {i}", self,  TilesetController, i, False, '', True
                ])
            )
        for i in range(0, NUMBER_OF_BACKGROUNDS):
            self._tree_level_iter.append(
                item_store.append(root, [
                    'skytemple-e-mapbg-symbolic', f"{_('Background')} {i + NUMBER_OF_TILESETS}",
                    self,  DungeonBgController, i, False, '', True
                ])
            )
        self._tree_level_iter.append(
            item_store.append(root, [
                'skytemple-e-dungeon-tileset-symbolic', _("Color Map"),
                self, ColvecController, i, False, '', True
            ])
        )
        self._colvec_pos = len(self._tree_level_iter)-1
        recursive_generate_item_store_row_label(self._tree_model[root])

    def handle_request(self, request: OpenRequest) -> Optional[Gtk.TreeIter]:
        if request.type == REQUEST_TYPE_DUNGEON_TILESET:
            return self._tree_level_iter[request.identifier]

    def get_colvec(self) -> Colvec:
        return self.dungeon_bin.get(f'colormap.colvec')
    
    def get_dma(self, item_id) -> Dma:
        return self.dungeon_bin.get(f'dungeon{item_id}.dma')

    def get_dpl(self, item_id) -> Dpl:
        return self.dungeon_bin.get(f'dungeon{item_id}.dpl')

    def get_dpla(self, item_id) -> Dpla:
        return self.dungeon_bin.get(f'dungeon{item_id}.dpla')

    def get_dpc(self, item_id) -> Dpc:
        return self.dungeon_bin.get(f'dungeon{item_id}.dpc')

    def get_dpci(self, item_id) -> Dpci:
        return self.dungeon_bin.get(f'dungeon{item_id}.dpci')

    def get_bg_dbg(self, item_id) -> Dbg:
        return self.dungeon_bin.get(f'dungeon_bg{item_id}.dbg')

    def get_bg_dpl(self, item_id) -> Dpl:
        return self.dungeon_bin.get(f'dungeon_bg{item_id}.dpl')

    def get_bg_dpla(self, item_id) -> Dpla:
        return self.dungeon_bin.get(f'dungeon_bg{item_id}.dpla')

    def get_bg_dpc(self, item_id) -> Dpc:
        return self.dungeon_bin.get(f'dungeon_bg{item_id}.dpc')

    def get_bg_dpci(self, item_id) -> Dpci:
        return self.dungeon_bin.get(f'dungeon_bg{item_id}.dpci')

    def mark_as_modified(self, item_id, is_background):
        self.project.mark_as_modified(DUNGEON_BIN)

        # Mark as modified in tree
        if is_background:
            item_id += NUMBER_OF_TILESETS
        row = self._tree_model[self._tree_level_iter[item_id]]
        recursive_up_item_store_mark_as_modified(row)
    
    def mark_colvec_as_modified(self):
        self.project.mark_as_modified(DUNGEON_BIN)
        # Mark as modified in tree
        row = self._tree_model[self._tree_level_iter[self._colvec_pos]]
        recursive_up_item_store_mark_as_modified(row)

    def nb_tilesets(self):
        return NUMBER_OF_TILESETS
