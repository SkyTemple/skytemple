#  Copyright 2020-2023 Capypara and the SkyTemple Contributors
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
from typing import Optional, List, Union

from gi.repository import Gtk
from skytemple.core.abstract_module import AbstractModule, DebuggingInfo
from skytemple.core.item_tree import ItemTree, ItemTreeEntry, ItemTreeEntryRef, RecursionType
from skytemple.core.model_context import ModelContext
from skytemple.core.module_controller import AbstractController
from skytemple.core.open_request import OpenRequest, REQUEST_TYPE_DUNGEON_TILESET
from skytemple.core.rom_project import RomProject, BinaryName
from skytemple.module.dungeon_graphics.controller.dungeon_bg import DungeonBgController, \
    BACKGROUNDS_NAMES, DungeonBgMainController
from skytemple.module.dungeon_graphics.controller.colvec import ColvecController
from skytemple.module.dungeon_graphics.controller.tileset import TilesetController, TILESETS_NAME, TilesetMainController
from skytemple.module.dungeon_graphics.controller.main import MainController, DUNGEON_GRAPHICS_NAME
from skytemple.module.dungeon_graphics.controller.trp_itm_img import ImgType, TrpItmImgController
from skytemple_files.common.types.file_types import FileType
from skytemple_files.container.dungeon_bin.model import DungeonBinPack
from skytemple_files.graphics.dbg.protocol import DbgProtocol
from skytemple_files.graphics.dma.protocol import DmaProtocol
from skytemple_files.graphics.dpc.protocol import DpcProtocol
from skytemple_files.graphics.dpci.protocol import DpciProtocol
from skytemple_files.graphics.dpl.protocol import DplProtocol
from skytemple_files.graphics.dpla.protocol import DplaProtocol
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

        self.dungeon_bin_context: ModelContext[DungeonBinPack]
        self._item_tree: ItemTree
        self._tree_level_iter: List[ItemTreeEntryRef] = []
        self._colvec_pos: int
        self._root_node: ItemTreeEntryRef

    def load_tree_items(self, item_tree: ItemTree):
        self.dungeon_bin_context = self.project.open_file_in_rom(
            DUNGEON_BIN, FileType.DUNGEON_BIN, static_data=self.project.get_rom_module().get_static_data(),
            threadsafe=True
        )

        root = self._root_node = item_tree.add_entry(None, ItemTreeEntry(
            icon='skytemple-e-dungeon-tileset-symbolic',
            name=DUNGEON_GRAPHICS_NAME,
            module=self,
            view_class=MainController,
            item_data=0
        ))
        tileset_root = item_tree.add_entry(root, ItemTreeEntry(
            icon='skytemple-e-dungeon-tileset-symbolic',
            name=TILESETS_NAME,
            module=self,
            view_class=TilesetMainController,
            item_data=0
        ))
        bg_root = item_tree.add_entry(root, ItemTreeEntry(
            icon='skytemple-e-mapbg-symbolic',
            name=BACKGROUNDS_NAMES,
            module=self,
            view_class=DungeonBgMainController,
            item_data=0
        ))
        self._item_tree = item_tree
        self._tree_level_iter = []
        for i in range(0, NUMBER_OF_TILESETS):
            self._tree_level_iter.append(
                item_tree.add_entry(tileset_root, ItemTreeEntry(
                    icon='skytemple-e-dungeon-tileset-symbolic',
                    name=f"{_('Tileset')} {i}",
                    module=self,
                    view_class=TilesetController,
                    item_data=i
                ))
            )
        for i in range(0, NUMBER_OF_BACKGROUNDS):
            self._tree_level_iter.append(
                item_tree.add_entry(bg_root, ItemTreeEntry(
                    icon='skytemple-e-mapbg-symbolic',
                    name=f"{_('Background')} {i + NUMBER_OF_TILESETS}",
                    module=self,
                    view_class=DungeonBgController,
                    item_data=i
                ))
            )
        self._tree_level_iter.append(
            item_tree.add_entry(root, ItemTreeEntry(
                icon='skytemple-e-graphics-symbolic',
                name=f"Traps",
                module=self,
                view_class=TrpItmImgController,
                item_data=ImgType.TRP
            ))
        )
        self._traps_pos = len(self._tree_level_iter) - 1
        self._tree_level_iter.append(
            item_tree.add_entry(root, ItemTreeEntry(
                icon='skytemple-e-graphics-symbolic',
                name=f"Items",
                module=self,
                view_class=TrpItmImgController,
                item_data=ImgType.ITM
            ))
        )
        self._items_pos = len(self._tree_level_iter) - 1
        self._tree_level_iter.append(
            item_tree.add_entry(root, ItemTreeEntry(
                icon='skytemple-e-dungeon-tileset-symbolic',
                name=_("Color Map"),
                module=self,
                view_class=ColvecController,
                item_data=i
            ))
        )
        self._colvec_pos = len(self._tree_level_iter) - 1

    def handle_request(self, request: OpenRequest) -> Optional[ItemTreeEntryRef]:
        if request.type == REQUEST_TYPE_DUNGEON_TILESET:
            return self._tree_level_iter[request.identifier]
        return None

    def get_colvec(self) -> Colvec:
        with self.dungeon_bin_context as dungeon_bin:
            return dungeon_bin.get(f'colormap.colvec')
    
    def get_dma(self, item_id) -> DmaProtocol:
        with self.dungeon_bin_context as dungeon_bin:
            return dungeon_bin.get(f'dungeon{item_id}.dma')

    def get_dpl(self, item_id) -> DplProtocol:
        with self.dungeon_bin_context as dungeon_bin:
            return dungeon_bin.get(f'dungeon{item_id}.dpl')

    def get_dpla(self, item_id) -> DplaProtocol:
        with self.dungeon_bin_context as dungeon_bin:
            return dungeon_bin.get(f'dungeon{item_id}.dpla')

    def get_dpc(self, item_id) -> DpcProtocol:
        with self.dungeon_bin_context as dungeon_bin:
            return dungeon_bin.get(f'dungeon{item_id}.dpc')

    def get_dpci(self, item_id) -> DpciProtocol:
        with self.dungeon_bin_context as dungeon_bin:
            return dungeon_bin.get(f'dungeon{item_id}.dpci')

    def get_bg_dbg(self, item_id) -> DbgProtocol:
        with self.dungeon_bin_context as dungeon_bin:
            return dungeon_bin.get(f'dungeon_bg{item_id}.dbg')

    def get_bg_dpl(self, item_id) -> DplProtocol:
        with self.dungeon_bin_context as dungeon_bin:
            return dungeon_bin.get(f'dungeon_bg{item_id}.dpl')

    def get_bg_dpla(self, item_id) -> DplaProtocol:
        with self.dungeon_bin_context as dungeon_bin:
            return dungeon_bin.get(f'dungeon_bg{item_id}.dpla')

    def get_bg_dpc(self, item_id) -> DpcProtocol:
        with self.dungeon_bin_context as dungeon_bin:
            return dungeon_bin.get(f'dungeon_bg{item_id}.dpc')

    def get_bg_dpci(self, item_id) -> DpciProtocol:
        with self.dungeon_bin_context as dungeon_bin:
            return dungeon_bin.get(f'dungeon_bg{item_id}.dpci')

    def mark_as_modified(self, item_id, is_background):
        self.project.mark_as_modified(DUNGEON_BIN)

        # Mark as modified in tree
        if is_background:
            item_id += NUMBER_OF_TILESETS
        self._item_tree.mark_as_modified(self._tree_level_iter[item_id], RecursionType.UP)
    
    def mark_colvec_as_modified(self):
        self.project.mark_as_modified(DUNGEON_BIN)
        # Mark as modified in tree
        self._item_tree.mark_as_modified(self._tree_level_iter[self._colvec_pos], RecursionType.UP)

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
        self._item_tree.mark_as_modified(self._root_node, RecursionType.UP)

    def collect_debugging_info(self, open_view: Union[AbstractController, Gtk.Widget]) -> Optional[DebuggingInfo]:
        if isinstance(open_view, DungeonBgController):
            pass  # todo
        if isinstance(open_view, ColvecController):
            pass  # todo
        if isinstance(open_view, TilesetController):
            pass  # todo
        if isinstance(open_view, TrpItmImgController):
            pass  # todo
        return None
