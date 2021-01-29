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
from typing import Optional

from gi.repository.Gtk import TreeStore, TreeIter
from ndspy.rom import NintendoDSRom

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.rom_project import RomProject
from skytemple.core.ui_utils import generate_item_store_row_label
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
        self._item_store = None
        self._root_node: Optional[TreeIter] = None
        self._static_data: Optional[Pmd2Data] = None
        self._rom = Optional[NintendoDSRom]

    def set_rom(self, rom: NintendoDSRom):
        self._rom = rom

    def controller_get_rom(self):
        """MAY ONLY BE USED BY THE CONTROLLER"""
        return self._rom

    def get_root_node(self):
        return self._root_node

    def load_tree_items(self, item_store: TreeStore, root_node: TreeIter):
        self._item_store = item_store
        self._root_node = item_store.append(root_node, [
            'skytemple-e-rom-symbolic', os.path.basename(self.project.filename), self,
            MainController, 0, False, '', True
        ])
        generate_item_store_row_label(item_store[self._root_node])

    def update_filename(self):
        self._item_store[self._root_node][1] = os.path.basename(self.project.filename)
        generate_item_store_row_label(self._item_store[self._root_node])

    def load_rom_data(self):
        self._static_data = self.project.load_rom_data()

    def get_static_data(self) -> Pmd2Data:
        return self._static_data
