#  Copyright 2020-2021 Capypara and the SkyTemple Contributors
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
from typing import Optional, List

from gi.repository import Gtk
from gi.repository.Gtk import TreeStore

from skytemple.core.abstract_module import AbstractModule, DebuggingInfo
from skytemple.core.model_context import ModelContext
from skytemple.core.module_controller import AbstractController
from skytemple.core.open_request import OpenRequest, REQUEST_TYPE_DUNGEON_TILESET
from skytemple.core.rom_project import RomProject, BinaryName
from skytemple.core.ui_utils import recursive_up_item_store_mark_as_modified, \
    recursive_generate_item_store_row_label
from skytemple.module.dungeon_graphics.controller.dungeon_bg import DungeonBgController, \
    BACKGROUNDS_NAMES, DungeonBgMainController
from skytemple.module.dungeon_graphics.controller.colvec import ColvecController
from skytemple.module.dungeon_graphics.controller.tileset import TilesetController, TILESETS_NAME, TilesetMainController
from skytemple.module.dungeon_graphics.controller.main import MainController, DUNGEON_GRAPHICS_NAME
from skytemple.module.dungeon_graphics.controller.trp_itm_img import ImgType, TrpItmImgController
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
from skytemple_files.hardcoded.dungeons import TilesetProperties, HardcodedDungeons

NUMBER_OF_TILESETS = 170
NUMBER_OF_BACKGROUNDS = 29
DUNGEON_BIN = 'DUNGEON/dungeon.bin'
ITEM_ICON_FILE = 'items.itm.img'
TRAP_ICON_FILE = 'traps.trp.img'
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

        self.dungeon_bin_context: Optional[DungeonBinPack] = None
        self._tree_model = None
        self._tree_level_iter = []
        self._colvec_pos = None
        self._root_node = None

    def load_tree_items(self, item_store: TreeStore, root_node):
        self.dungeon_bin_context: ModelContext[DungeonBinPack] = self.project.open_file_in_rom(
            DUNGEON_BIN, FileType.DUNGEON_BIN, static_data=self.project.get_rom_module().get_static_data(),
            threadsafe=True
        )

        root = self._root_node = item_store.append(root_node, [
            'skytemple-e-dungeon-tileset-symbolic', DUNGEON_GRAPHICS_NAME, self, MainController, 0, False, '', True
        ])
        tileset_root = item_store.append(root, [
            'skytemple-e-dungeon-tileset-symbolic', TILESETS_NAME, self, TilesetMainController, 0, False, '', True
        ])
        bg_root = item_store.append(root, [
            'skytemple-e-mapbg-symbolic', BACKGROUNDS_NAMES, self, DungeonBgMainController, 0, False, '', True
        ])
        self._tree_model = item_store
        self._tree_level_iter = []
        for i in range(0, NUMBER_OF_TILESETS):
            self._tree_level_iter.append(
                item_store.append(tileset_root, [
                    'skytemple-e-dungeon-tileset-symbolic', f"{_('Tileset')} {i}", self,  TilesetController, i, False, '', True
                ])
            )
        for i in range(0, NUMBER_OF_BACKGROUNDS):
            self._tree_level_iter.append(
                item_store.append(bg_root, [
                    'skytemple-e-mapbg-symbolic', f"{_('Background')} {i + NUMBER_OF_TILESETS}",
                    self,  DungeonBgController, i, False, '', True
                ])
            )
        self._tree_level_iter.append(
            item_store.append(root, [
                'skytemple-e-graphics-symbolic', f"Traps",
                self, TrpItmImgController, ImgType.TRP, False, '', True
            ])
        )
        self._traps_pos = len(self._tree_level_iter)-1
        self._tree_level_iter.append(
            item_store.append(root, [
                'skytemple-e-graphics-symbolic', f"Items",
                self, TrpItmImgController, ImgType.ITM, False, '', True
            ])
        )
        self._items_pos = len(self._tree_level_iter)-1
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
        with self.dungeon_bin_context as dungeon_bin:
            return dungeon_bin.get(f'colormap.colvec')
    
    def get_dma(self, item_id) -> Dma:
        with self.dungeon_bin_context as dungeon_bin:
            return dungeon_bin.get(f'dungeon{item_id}.dma')

    def get_dpl(self, item_id) -> Dpl:
        with self.dungeon_bin_context as dungeon_bin:
            return dungeon_bin.get(f'dungeon{item_id}.dpl')

    def get_dpla(self, item_id) -> Dpla:
        with self.dungeon_bin_context as dungeon_bin:
            return dungeon_bin.get(f'dungeon{item_id}.dpla')

    def get_dpc(self, item_id) -> Dpc:
        with self.dungeon_bin_context as dungeon_bin:
            return dungeon_bin.get(f'dungeon{item_id}.dpc')

    def get_dpci(self, item_id) -> Dpci:
        with self.dungeon_bin_context as dungeon_bin:
            return dungeon_bin.get(f'dungeon{item_id}.dpci')

    def get_bg_dbg(self, item_id) -> Dbg:
        with self.dungeon_bin_context as dungeon_bin:
            return dungeon_bin.get(f'dungeon_bg{item_id}.dbg')

    def get_bg_dpl(self, item_id) -> Dpl:
        with self.dungeon_bin_context as dungeon_bin:
            return dungeon_bin.get(f'dungeon_bg{item_id}.dpl')

    def get_bg_dpla(self, item_id) -> Dpla:
        with self.dungeon_bin_context as dungeon_bin:
            return dungeon_bin.get(f'dungeon_bg{item_id}.dpla')

    def get_bg_dpc(self, item_id) -> Dpc:
        with self.dungeon_bin_context as dungeon_bin:
            return dungeon_bin.get(f'dungeon_bg{item_id}.dpc')

    def get_bg_dpci(self, item_id) -> Dpci:
        with self.dungeon_bin_context as dungeon_bin:
            return dungeon_bin.get(f'dungeon_bg{item_id}.dpci')

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

    def get_icons(self, img_type):
        if img_type == ImgType.ITM:
            with self.dungeon_bin_context as dungeon_bin:
                return dungeon_bin.get(ITEM_ICON_FILE)
        elif img_type == ImgType.TRP:
            with self.dungeon_bin_context as dungeon_bin:
                return dungeon_bin.get(TRAP_ICON_FILE)
        else:
            raise ValueError("Invalid item type")

    def mark_icons_as_modified(self, img_type, img_model):
        if img_type == ImgType.ITM:
            with self.dungeon_bin_context as dungeon_bin:
                dungeon_bin.set(ITEM_ICON_FILE, img_model)
        elif img_type == ImgType.TRP:
            with self.dungeon_bin_context as dungeon_bin:
                dungeon_bin.set(TRAP_ICON_FILE, img_model)
        else:
            raise ValueError("Invalid item type")
        self.project.mark_as_modified(DUNGEON_BIN)

    def get_tileset_properties(self) -> List[TilesetProperties]:
        return HardcodedDungeons.get_tileset_properties(
            self.project.get_binary(BinaryName.OVERLAY_10),
            self.project.get_rom_module().get_static_data()
        )

    def set_tileset_properties(self, lst: List[TilesetProperties]):
        self.project.modify_binary(
            BinaryName.OVERLAY_10, lambda binary: HardcodedDungeons.set_tileset_properties(
                lst, binary, self.project.get_rom_module().get_static_data()
        ))
        row = self._tree_model[self._root_node]
        recursive_up_item_store_mark_as_modified(row)

    def collect_debugging_info(self, open_controller: AbstractController) -> Optional[DebuggingInfo]:
        if isinstance(open_controller, DungeonBgController):
            pass  # todo
        if isinstance(open_controller, ColvecController):
            pass  # todo
        if isinstance(open_controller, TilesetController):
            pass  # todo
        if isinstance(open_controller, TrpItmImgController):
            pass  # todo
        return None
