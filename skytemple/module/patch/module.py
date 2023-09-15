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
from skytemple.core.abstract_module import AbstractModule
from skytemple.core.item_tree import ItemTreeEntryRef, ItemTree, ItemTreeEntry, RecursionType
from skytemple.core.widget.status_page import StStatusPageData, StStatusPage
from skytemple.module.patch.controller.cot import CotController
from skytemple.module.patch.controller.item_effects import ItemEffectsController
from skytemple.module.patch.controller.move_effects import MoveEffectsController
from skytemple.module.patch.controller.pmdsky_debug import PmdSkyDebugController
from skytemple.module.patch.controller.sp_effects import SPEffectsController
from skytemple_files.data.data_cd.handler import DataCDHandler
from skytemple.core.rom_project import RomProject
from skytemple.module.patch.controller.asm import AsmController
from skytemple_files.common.i18n_util import _
from skytemple_files.data.data_cd.model import DataCD
from skytemple_files.data.val_list.handler import ValListHandler
from skytemple_files.data.val_list.model import ValList

SP_EFFECTS = 'BALANCE/process.bin'
MOVE_EFFECTS = 'BALANCE/waza_cd.bin'
ITEM_EFFECTS = 'BALANCE/item_cd.bin'
METRONOME_POOL = 'BALANCE/metrono.bin'


MAIN_VIEW_DATA = StStatusPageData(
    icon_name='skytemple-illust-patch',
    title=_('Patches'),
    description=_("In this section you can apply built-in ASM patches, your own ASM patches and custom\nitem-, move- and "
                  "special process effects written in Assembler.\n\nYou will also find information on how to write your own\n"
                  "patches and effects in the C and Rust programming languages.\n\nAdditionally you can browse all symbols "
                  "and functions\nin the game known to SkyTemple.")
)


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

        self._item_tree: ItemTree
        self._asm_iter: ItemTreeEntryRef
        self._asm_special_procs: ItemTreeEntryRef
        self._asm_item_effects: ItemTreeEntryRef
        self._asm_move_effects: ItemTreeEntryRef


    def load_tree_items(self, item_tree: ItemTree):
        root = item_tree.add_entry(None, ItemTreeEntry(
            icon='skytemple-e-patch-symbolic',
            name=MAIN_VIEW_DATA.title,
            module=self,
            view_class=StStatusPage,
            item_data=MAIN_VIEW_DATA
        ))

        self._asm_iter = item_tree.add_entry(root, ItemTreeEntry(
            icon='skytemple-e-patch-symbolic',
            name=_('ASM'),
            module=self,
            view_class=AsmController,
            item_data=0
        ))

        self._asm_special_procs = item_tree.add_entry(self._asm_iter, ItemTreeEntry(
            icon='skytemple-e-special-symbolic',
            name=_('Special Process Effects'),
            module=self,
            view_class=SPEffectsController,
            item_data=0
        ))

        self._asm_item_effects = item_tree.add_entry(self._asm_iter, ItemTreeEntry(
            icon='skytemple-e-item-symbolic',
            name=_('Item Effects'),
            module=self,
            view_class=ItemEffectsController,
            item_data=0
        ))

        self._asm_move_effects = item_tree.add_entry(self._asm_iter, ItemTreeEntry(
            icon='skytemple-e-move-symbolic',
            name=_('Move Effects'),
            module=self,
            view_class=MoveEffectsController,
            item_data=0
        ))

        item_tree.add_entry(root, ItemTreeEntry(
            icon='skytemple-e-patch-symbolic',
            name=_('C / Rust'),
            module=self,
            view_class=CotController,
            item_data=0
        ))

        item_tree.add_entry(root, ItemTreeEntry(
            icon='skytemple-e-patch-symbolic',
            name=_('Symbols'),
            module=self,
            view_class=PmdSkyDebugController,
            item_data=0
        ))

        self._item_tree = item_tree

    def has_sp_effects(self):
        return self.project.file_exists(SP_EFFECTS)

    def get_sp_effects(self) -> DataCD:
        return self.project.open_file_in_rom(SP_EFFECTS, DataCDHandler)

    def mark_sp_effects_as_modified(self):
        """Mark as modified"""
        self.project.mark_as_modified(SP_EFFECTS)
        # Mark as modified in tree
        self._item_tree.mark_as_modified(self._asm_special_procs, RecursionType.UP)

    def has_item_effects(self):
        return self.project.file_exists(ITEM_EFFECTS)

    def get_item_effects(self) -> DataCD:
        return self.project.open_file_in_rom(ITEM_EFFECTS, DataCDHandler)

    def mark_item_effects_as_modified(self):
        """Mark as modified"""
        self.project.mark_as_modified(ITEM_EFFECTS)
        # Mark as modified in tree
        self._item_tree.mark_as_modified(self._asm_item_effects, RecursionType.UP)

    def has_move_effects(self):
        return self.project.file_exists(MOVE_EFFECTS)

    def get_move_effects(self) -> DataCD:
        return self.project.open_file_in_rom(MOVE_EFFECTS, DataCDHandler)

    def mark_move_effects_as_modified(self):
        """Mark as modified"""
        self.project.mark_as_modified(MOVE_EFFECTS)
        # Mark as modified in tree
        self._item_tree.mark_as_modified(self._asm_move_effects, RecursionType.UP)

    def has_metronome_pool(self):
        return self.project.file_exists(METRONOME_POOL)

    def get_metronome_pool(self) -> ValList:
        return self.project.open_file_in_rom(METRONOME_POOL, ValListHandler)

    def mark_metronome_pool_as_modified(self):
        """Mark as modified"""
        self.project.mark_as_modified(METRONOME_POOL)
        # Mark as modified in tree
        self._item_tree.mark_as_modified(self._asm_move_effects, RecursionType.UP)

    def mark_asm_patches_as_modified(self):
        """Mark as modified"""
        # We don't have to mark anything at the project as modified, the
        # binaries are already patched.
        self.project.force_mark_as_modified()
        # Mark as modified in tree
        self._item_tree.mark_as_modified(self._asm_iter, RecursionType.UP)
