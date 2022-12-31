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
from typing import Optional

from gi.repository import Gtk
from gi.repository.Gtk import TreeStore

from skytemple.core.abstract_module import AbstractModule
from skytemple.module.patch.controller.cot import CotController
from skytemple.module.patch.controller.item_effects import ItemEffectsController
from skytemple.module.patch.controller.main import PATCHES, MainController
from skytemple.module.patch.controller.move_effects import MoveEffectsController
from skytemple.module.patch.controller.pmdsky_debug import PmdSkyDebugController
from skytemple.module.patch.controller.sp_effects import SPEffectsController
from skytemple_files.data.data_cd.handler import DataCDHandler
from skytemple.core.rom_project import RomProject
from skytemple.core.ui_utils import recursive_up_item_store_mark_as_modified, recursive_generate_item_store_row_label
from skytemple.module.patch.controller.asm import AsmController
from skytemple_files.common.i18n_util import _
from skytemple_files.data.data_cd.model import DataCD
from skytemple_files.data.val_list.handler import ValListHandler
from skytemple_files.data.val_list.model import ValList

SP_EFFECTS = 'BALANCE/process.bin'
MOVE_EFFECTS = 'BALANCE/waza_cd.bin'
ITEM_EFFECTS = 'BALANCE/item_cd.bin'
METRONOME_POOL = 'BALANCE/metrono.bin'


class PatchModule(AbstractModule):
    """Module to apply ASM based ROM patches."""
    @classmethod
    def depends_on(cls):
        return []

    @classmethod
    def sort_order(cls):
        return 10

    def __init__(self, rom_project: RomProject):
        self.project = rom_project

        self._tree_model: Gtk.TreeModel
        self._asm_iter: Gtk.TreeIter
        self._asm_special_procs: Gtk.TreeIter
        self._asm_item_effects: Gtk.TreeIter
        self._asm_move_effects: Gtk.TreeIter
        self._c_of_time_iter: Gtk.TreeIter
        self.pmdsky_debug_iter: Gtk.TreeIter


    def load_tree_items(self, item_store: TreeStore, root_node):

        root = item_store.append(root_node, [
            'skytemple-e-patch-symbolic', PATCHES, self, MainController, 0, False, '', True
        ])

        self._asm_iter = item_store.append(root, [
            'skytemple-e-patch-symbolic', _('ASM'), self, AsmController, 0, False, '', True
        ])
        self._asm_special_procs = item_store.append(self._asm_iter, [
            'skytemple-e-special-symbolic', _('Special Process Effects'), self, SPEffectsController, 0, False, '', True
        ])
        self._asm_item_effects = item_store.append(self._asm_iter, [
            'skytemple-e-item-symbolic', _('Item Effects'), self, ItemEffectsController, 0, False, '', True
        ])
        self._asm_move_effects = item_store.append(self._asm_iter, [
            'skytemple-e-move-symbolic', _('Move Effects'), self, MoveEffectsController, 0, False, '', True
        ])

        self._c_of_time_iter = item_store.append(root, [
            'skytemple-e-patch-symbolic', _('C / Rust'), self, CotController, 0, False, '', True
        ])

        self.pmdsky_debug_iter = item_store.append(root, [
            'skytemple-e-patch-symbolic', _('Symbols'), self, PmdSkyDebugController, 0, False, '', True
        ])

        recursive_generate_item_store_row_label(item_store[root])
        self._tree_model = item_store

    def has_sp_effects(self):
        return self.project.file_exists(SP_EFFECTS)

    def get_sp_effects(self) -> DataCD:
        return self.project.open_file_in_rom(SP_EFFECTS, DataCDHandler)

    def mark_sp_effects_as_modified(self):
        """Mark as modified"""
        self.project.mark_as_modified(SP_EFFECTS)
        # Mark as modified in tree
        row = self._tree_model[self._asm_special_procs]
        recursive_up_item_store_mark_as_modified(row)

    def has_item_effects(self):
        return self.project.file_exists(ITEM_EFFECTS)

    def get_item_effects(self) -> DataCD:
        return self.project.open_file_in_rom(ITEM_EFFECTS, DataCDHandler)

    def mark_item_effects_as_modified(self):
        """Mark as modified"""
        self.project.mark_as_modified(ITEM_EFFECTS)
        # Mark as modified in tree
        row = self._tree_model[self._asm_item_effects]
        recursive_up_item_store_mark_as_modified(row)

    def has_move_effects(self):
        return self.project.file_exists(MOVE_EFFECTS)

    def get_move_effects(self) -> DataCD:
        return self.project.open_file_in_rom(MOVE_EFFECTS, DataCDHandler)

    def mark_move_effects_as_modified(self):
        """Mark as modified"""
        self.project.mark_as_modified(MOVE_EFFECTS)
        # Mark as modified in tree
        row = self._tree_model[self._asm_move_effects]
        recursive_up_item_store_mark_as_modified(row)

    def has_metronome_pool(self):
        return self.project.file_exists(METRONOME_POOL)

    def get_metronome_pool(self) -> ValList:
        return self.project.open_file_in_rom(METRONOME_POOL, ValListHandler)

    def mark_metronome_pool_as_modified(self):
        """Mark as modified"""
        self.project.mark_as_modified(METRONOME_POOL)
        # Mark as modified in tree
        row = self._tree_model[self._asm_move_effects]
        recursive_up_item_store_mark_as_modified(row)

    def mark_asm_patches_as_modified(self):
        """Mark as modified"""
        # We don't have to mark anything at the project as modified, the
        # binaries are already patched.
        self.project.force_mark_as_modified()
        # Mark as modified in tree
        row = self._tree_model[self._asm_iter]
        recursive_up_item_store_mark_as_modified(row)
