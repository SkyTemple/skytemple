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
from gi.repository.Gtk import TreeStore

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.rom_project import RomProject
from skytemple.core.ui_utils import recursive_up_item_store_mark_as_modified, generate_item_store_row_label, \
    recursive_generate_item_store_row_label
from skytemple.module.moves_items.controller.main_moves import MainMovesController, MOVES
from skytemple.module.moves_items.controller.main_items import MainItemsController, ITEMS
from skytemple.module.moves_items.controller.item_lists import ItemListsController
from skytemple.module.moves_items.controller.item_effects import ItemEffectsController
from skytemple.module.moves_items.controller.move_effects import MoveEffectsController
from skytemple_files.data.data_cd.handler import DataCDHandler
from skytemple_files.data.val_list.handler import ValListHandler
from skytemple_files.list.items.handler import ItemListHandler
from skytemple_files.dungeon_data.mappa_bin.item_list import MappaItemList
from skytemple_files.common.i18n_util import _

ITEM_LISTS = 'TABLEDAT/list_%02d.bin'
METRONOME_POOL = 'BALANCE/metrono.bin'
MOVE_EFFECTS = 'BALANCE/waza_cd.bin'
ITEM_EFFECTS = 'BALANCE/item_cd.bin'


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

        self._tree_model = None
        self._item_lists_tree_iter = None
        self._item_effects_tree_iter = None
        self._move_effects_tree_iter = None

    def load_tree_items(self, item_store: TreeStore, root_node):
        root_items = item_store.append(root_node, [
            'skytemple-view-list-symbolic', ITEMS, self, MainItemsController, 0, False, '', True
        ])
        root_moves = item_store.append(root_node, [
            'skytemple-view-list-symbolic', MOVES, self, MainMovesController, 0, False, '', True
        ])
        self._item_lists_tree_iter = item_store.append(root_items, [
            'skytemple-view-list-symbolic', _('Item Lists'), self, ItemListsController, 0, False, '', True
        ])
        self._item_effects_tree_iter = item_store.append(root_items, [
            'skytemple-view-list-symbolic', _('Item Effects'), self, ItemEffectsController, 0, False, '', True
        ])
        self._move_effects_tree_iter = item_store.append(root_moves, [
            'skytemple-view-list-symbolic', _('Move Effects'), self, MoveEffectsController, 0, False, '', True
        ])
        recursive_generate_item_store_row_label(item_store[root_items])
        recursive_generate_item_store_row_label(item_store[root_moves])
        self._tree_model = item_store

    def has_item_effects(self):
        return self.project.file_exists(ITEM_EFFECTS)
    
    def get_item_effects(self):
        return self.project.open_file_in_rom(ITEM_EFFECTS, DataCDHandler)
    
    def mark_item_effects_as_modified(self):
        """Mark as modified"""
        self.project.mark_as_modified(ITEM_EFFECTS)
        # Mark as modified in tree
        row = self._tree_model[self._item_effects_tree_iter]
        recursive_up_item_store_mark_as_modified(row)
        
    def has_metronome_pool(self):
        return self.project.file_exists(METRONOME_POOL)
    
    def get_metronome_pool(self):
        return self.project.open_file_in_rom(METRONOME_POOL, ValListHandler)
    
    def mark_metronome_pool_as_modified(self):
        """Mark as modified"""
        self.project.mark_as_modified(METRONOME_POOL)
        # Mark as modified in tree
        row = self._tree_model[self._move_effects_tree_iter]
        recursive_up_item_store_mark_as_modified(row)
    
    def has_move_effects(self):
        return self.project.file_exists(MOVE_EFFECTS)
    
    def get_move_effects(self):
        return self.project.open_file_in_rom(MOVE_EFFECTS, DataCDHandler)
    
    def mark_move_effects_as_modified(self):
        """Mark as modified"""
        self.project.mark_as_modified(MOVE_EFFECTS)
        # Mark as modified in tree
        row = self._tree_model[self._move_effects_tree_iter]
        recursive_up_item_store_mark_as_modified(row)
    
    def has_item_lists(self):
        return self.project.file_exists(ITEM_LISTS%0)

    def get_item_list(self, list_id) -> MappaItemList:
        static_data = self.project.get_rom_module().get_static_data()
        return self.project.open_file_in_rom(ITEM_LISTS%list_id, ItemListHandler, items=static_data.dungeon_data.items)
    
    def mark_item_list_as_modified(self, list_id):
        """Mark as modified"""
        self.project.mark_as_modified(ITEM_LISTS%list_id)
        # Mark as modified in tree
        row = self._tree_model[self._item_lists_tree_iter]
        recursive_up_item_store_mark_as_modified(row)
