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
from typing import Dict, Tuple, Optional, List

from gi.repository import Gtk
from gi.repository.Gtk import TreeStore, TreeIter
from range_typed_integers import u16

from skytemple.core.abstract_module import AbstractModule, DebuggingInfo
from skytemple.core.module_controller import AbstractController
from skytemple.core.rom_project import RomProject
from skytemple.core.string_provider import StringType
from skytemple.core.ui_utils import recursive_up_item_store_mark_as_modified, \
    recursive_generate_item_store_row_label
from skytemple.module.moves_items.controller.item import ItemController
from skytemple.module.moves_items.controller.main_moves import MainMovesController, MOVES
from skytemple.module.moves_items.controller.main_items import MainItemsController, ITEMS
from skytemple.module.moves_items.controller.item_lists import ItemListsController
from skytemple.module.moves_items.controller.item_keys import ItemKeysController
from skytemple.module.moves_items.controller.move import MoveController
from skytemple_files.common.ppmdu_config.dungeon_data import Pmd2DungeonItemCategory
from skytemple_files.common.types.file_types import FileType
from skytemple_files.data.item_p.protocol import ItemPProtocol, ItemPEntryProtocol
from skytemple_files.data.item_s_p.model import ItemSP, ItemSPEntry

from skytemple_files.data.waza_p.protocol import WazaMoveProtocol, WazaPProtocol
from skytemple_files.list.items.handler import ItemListHandler
from skytemple_files.data.val_list.handler import ValListHandler
from skytemple_files.dungeon_data.mappa_bin.protocol import MappaItemListProtocol
from skytemple_files.common.i18n_util import _

MOVE_FILE = 'BALANCE/waza_p.bin'
ITEM_S_FILE = 'BALANCE/item_s_p.bin'
ITEM_FILE = 'BALANCE/item_p.bin'
ITEM_LISTS = 'TABLEDAT/list_%02d.bin'
FIRST_EXCLUSIVE_ITEM_ID = 444
logger = logging.getLogger(__name__)


class MovesItemsModule(AbstractModule):
    """Module to modify move and item lists."""

    @classmethod
    def depends_on(cls):
        return []

    @classmethod
    def sort_order(cls):
        return 75

    def __init__(self, rom_project: RomProject):
        self.project = rom_project

        self._tree_model: Gtk.TreeModel
        self._item_lists_tree_iter: Dict[str, Gtk.TreeIter] = {}
        self._item_keys_tree_iter: Gtk.TreeIter
        self.item_iters: Dict[int, TreeIter] = {}
        self.move_iters: Dict[int, TreeIter] = {}

    def load_tree_items(self, item_store: TreeStore, root_node):
        root_items = item_store.append(root_node, [
            'skytemple-e-item-symbolic', ITEMS, self, MainItemsController, 0, False, '', True
        ])
        root_moves = item_store.append(root_node, [
            'skytemple-e-move-symbolic', MOVES, self, MainMovesController, 0, False, '', True
        ])
        self._item_lists_tree_iter = item_store.append(root_items, [
            'skytemple-view-list-symbolic', _('Item Lists'), self, ItemListsController, 0, False, '', True
        ])
        self._item_keys_tree_iter = item_store.append(root_items, [
            'skytemple-view-list-symbolic', _('Item Sort Keys'), self, ItemKeysController, 0, False, '', True
        ])

        logger.debug("Building item tree...")
        for i, _item in enumerate(self.get_item_p().item_list):
            name = self.project.get_string_provider().get_value(StringType.ITEM_NAMES, i)
            self.item_iters[i] = (item_store.append(root_items, [
                'skytemple-e-item-symbolic', f'#{i:04}: {name}', self, ItemController, i, False, '', True
            ]))

        logger.debug("Building move tree...")
        for i, __item in enumerate(self.get_waza_p().moves):
            name = self.project.get_string_provider().get_value(StringType.MOVE_NAMES, i)
            self.move_iters[i] = (item_store.append(root_moves, [
                'skytemple-e-move-symbolic', f'#{i:04}: {name}', self, MoveController, i, False, '', True
            ]))
        logger.debug("Done building trees.")

        recursive_generate_item_store_row_label(item_store[root_items])
        recursive_generate_item_store_row_label(item_store[root_moves])
        self._tree_model = item_store

    def has_item_lists(self):
        return self.project.file_exists(ITEM_LISTS % 0)

    def get_item_list(self, list_id) -> MappaItemListProtocol:
        static_data = self.project.get_rom_module().get_static_data()
        return self.project.open_file_in_rom(ITEM_LISTS % list_id, ItemListHandler,
                                             items=static_data.dungeon_data.items)

    def mark_item_list_as_modified(self, list_id):
        """Mark as modified"""
        self.project.mark_as_modified(ITEM_LISTS % list_id)
        # Mark as modified in tree
        row = self._tree_model[self._item_lists_tree_iter]
        recursive_up_item_store_mark_as_modified(row)

    def get_item_p(self) -> ItemPProtocol:
        return self.project.open_file_in_rom(ITEM_FILE, FileType.ITEM_P)

    def get_item_s_p(self) -> ItemSP:
        return self.project.open_file_in_rom(ITEM_S_FILE, FileType.ITEM_SP)

    def get_item(self, item_id) -> Tuple[ItemPEntryProtocol, Optional[ItemSPEntry]]:
        if item_id >= FIRST_EXCLUSIVE_ITEM_ID:
            return self.get_item_p().item_list[item_id], self.get_item_s_p().item_list[item_id - FIRST_EXCLUSIVE_ITEM_ID]
        return self.get_item_p().item_list[item_id], None

    def mark_item_as_modified(self, item_id):
        self.project.mark_as_modified(ITEM_FILE)
        self.project.get_string_provider().mark_as_modified()
        if item_id >= FIRST_EXCLUSIVE_ITEM_ID:
            self.project.mark_as_modified(ITEM_S_FILE)
        # Mark as modified in tree
        row = self._tree_model[self.item_iters[item_id]]
        recursive_up_item_store_mark_as_modified(row)

        # Reload item categories:
        conf = self.project.get_rom_module().get_static_data()
        cats: Dict[Pmd2DungeonItemCategory, List[int]] = {x: [] for x in conf.dungeon_data.item_categories.values()}

        for idx, entry in enumerate(self.get_item_p().item_list):
            cats[conf.dungeon_data.item_categories[entry.category]].append(idx)

        for category in conf.dungeon_data.item_categories.values():
            category.items = cats[category]

    def get_waza_p(self) -> WazaPProtocol:
        return self.project.open_file_in_rom(MOVE_FILE, FileType.WAZA_P)

    def get_move(self, move_id) -> WazaMoveProtocol:
        return self.get_waza_p().moves[move_id]

    def get_i2n(self, in_lang: str) -> List[u16]:
        sp = self.project.get_string_provider()
        lang = sp.get_language(in_lang)
        i2n_model = self.project.open_file_in_rom(f"BALANCE/{lang.sort_lists.i2n}", ValListHandler)
        return i2n_model.get_list()
    
    def set_i2n(self, in_lang: str, values: List[u16]):
        sp = self.project.get_string_provider()
        lang = sp.get_language(in_lang)
        i2n_model = self.project.open_file_in_rom(f"BALANCE/{lang.sort_lists.i2n}", ValListHandler)
        i2n_model.set_list(values)
        self.project.mark_as_modified(f"BALANCE/{lang.sort_lists.i2n}")
        row = self._tree_model[self._item_keys_tree_iter]  # type: ignore
        recursive_up_item_store_mark_as_modified(row)

    def mark_move_as_modified(self, move_id):
        self.project.mark_as_modified(MOVE_FILE)
        self.project.get_string_provider().mark_as_modified()
        # Mark as modified in tree
        row = self._tree_model[self.move_iters[move_id]]
        recursive_up_item_store_mark_as_modified(row)

    def collect_debugging_info(self, open_controller: AbstractController) -> Optional[DebuggingInfo]:
        if isinstance(open_controller, MoveController):
            pass  # todo
        if isinstance(open_controller, ItemController):
            pass  # todo
        if isinstance(open_controller, ItemKeysController):
            pass  # todo
        if isinstance(open_controller, ItemListsController):
            pass  # todo
        return None
