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
import os
from typing import Optional
from ndspy.rom import NintendoDSRom

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.item_tree import ItemTree, ItemTreeEntryRef, ItemTreeEntry, RecursionType
from skytemple.core.rom_project import RomProject
from skytemple.core.ui_utils import assert_not_none
from skytemple.module.rom.controller.main import MainController
from skytemple_files.common.ppmdu_config.data import Pmd2Data


class RomModule(AbstractModule):
    @classmethod
    def depends_on(cls):
        return []

    @classmethod
    def sort_order(cls):
        return 0

    def __init__(self, rom_project: RomProject):
        """Main ROM metadata management module."""
        self.project = rom_project
        self._item_tree: Optional[ItemTree] = None
        self._root_node: Optional[ItemTreeEntryRef] = None
        self._static_data: Optional[Pmd2Data] = None
        self._rom = Optional[NintendoDSRom]

    def set_rom(self, rom: NintendoDSRom):
        self._rom = rom

    def controller_get_rom(self):
        """MAY ONLY BE USED BY THE CONTROLLER"""
        return self._rom

    def get_root_node(self) -> ItemTreeEntryRef:
        assert self._root_node is not None
        return self._root_node

    def load_tree_items(self, item_tree: ItemTree):
        self._item_tree = item_tree
        self._root_node = item_tree.set_root(ItemTreeEntry(
            icon='skytemple-e-rom-symbolic',
            name=os.path.basename(self.project.filename),
            module=self,
            view_class=MainController,
            item_data=0
        ))

    def update_filename(self):
        assert self._item_tree is not None
        assert self._root_node is not None
        old_entry = self._root_node.entry()
        self._root_node.update(ItemTreeEntry(
            icon=old_entry.icon,
            name=os.path.basename(self.project.filename),
            module=old_entry.module,
            view_class=old_entry.view_class,
            item_data=old_entry.item_data
        ))

    def load_rom_data(self):
        if self._static_data is None:
            self._static_data = self.project.load_rom_data()

    def get_static_data(self) -> Pmd2Data:
        return assert_not_none(self._static_data)

    def mark_as_modified(self):
        assert self._item_tree is not None
        assert self._root_node is not None
        self.project.force_mark_as_modified()
        self._item_tree.mark_as_modified(self._root_node, RecursionType.UP)
