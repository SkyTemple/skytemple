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
from typing import Optional

from gi.repository.Gtk import TreeStore

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.rom_project import RomProject
from skytemple.core.ui_utils import recursive_generate_item_store_row_label, recursive_up_item_store_mark_as_modified
from skytemple.module.misc_graphics.controller.w16 import W16Controller
from skytemple.module.misc_graphics.controller.wte_wtu import WteWtuController
from skytemple.module.misc_graphics.controller.zmappat import ZMappaTController
from skytemple.module.misc_graphics.controller.main import MainController, MISC_GRAPHICS
from skytemple_files.common.types.file_types import FileType
from skytemple_files.container.dungeon_bin.model import DungeonBinPack
from skytemple_files.graphics.wte.model import Wte
from skytemple_files.graphics.wtu.model import Wtu
from skytemple_files.graphics.zmappat.model import ZMappaT

W16_FILE_EXT = 'w16'
WTE_FILE_EXT = 'wte'
WTU_FILE_EXT = 'wtu'
ZMAPPAT_FILE_EXT = 'zmappat'
DUNGEON_BIN_PATH = 'DUNGEON/dungeon.bin'


class WteOpenSpec:
    def __init__(self, wte_filename: str, wtu_filename: str = None, in_dungeon_bin=False):
        self.wte_filename = wte_filename
        self.wtu_filename = wtu_filename
        self.in_dungeon_bin = in_dungeon_bin


class MiscGraphicsModule(AbstractModule):
    @classmethod
    def depends_on(cls):
        return []

    @classmethod
    def sort_order(cls):
        return 800

    def __init__(self, rom_project: RomProject):
        """Various misc. graphics formats."""
        self.project = rom_project
        self.list_of_w16s = self.project.get_files_with_ext(W16_FILE_EXT)
        self.list_of_wtes = self.project.get_files_with_ext(WTE_FILE_EXT)
        self.list_of_wtus = self.project.get_files_with_ext(WTU_FILE_EXT)
        self.dungeon_bin: Optional[DungeonBinPack] = None
        self.list_of_wtes_dungeon_bin = None
        self.list_of_wtus_dungeon_bin = None
        self.list_of_zmappats_dungeon_bin = None

        self._tree_model = None
        self._tree_level_iter = {}
        self._tree_level_dungeon_iter = {}

    def load_tree_items(self, item_store: TreeStore, root_node):
        self.dungeon_bin: DungeonBinPack = self.project.open_file_in_rom(
            DUNGEON_BIN_PATH, FileType.DUNGEON_BIN,
            static_data=self.project.get_rom_module().get_static_data()
        )
        self.list_of_wtes_dungeon_bin = self.dungeon_bin.get_files_with_ext(WTE_FILE_EXT)
        self.list_of_wtus_dungeon_bin = self.dungeon_bin.get_files_with_ext(WTU_FILE_EXT)
        self.list_of_zmappats_dungeon_bin = self.dungeon_bin.get_files_with_ext(ZMAPPAT_FILE_EXT)

        root = item_store.append(root_node, [
            'skytemple-e-graphics-symbolic', MISC_GRAPHICS, self, MainController, 0, False, '', True
        ])
        self._tree_model = item_store
        self._tree_level_iter = {}
        self._tree_level_dungeon_iter = {}

        sorted_entries = {}
        for name in self.list_of_w16s:
            sorted_entries[name] = False
        for name in self.list_of_wtes:
            sorted_entries[name] = True
        sorted_entries = {k: v for k, v in sorted(sorted_entries.items(), key=lambda item: item[0])}

        for i, (name, is_wte) in enumerate(sorted_entries.items()):
            if not is_wte:
                self._tree_level_iter[name] = item_store.append(root, [
                    'skytemple-e-graphics-symbolic', name, self,  W16Controller,
                    self.list_of_w16s.index(name), False, '', True
                ])
            else:
                wtu_name = name[:-3] + WTU_FILE_EXT
                if name[:-3] + WTU_FILE_EXT not in self.list_of_wtus:
                    wtu_name = None
                self._tree_level_iter[name] = item_store.append(root, [
                    'skytemple-e-graphics-symbolic', name, self,  WteWtuController, WteOpenSpec(
                        name, wtu_name, False
                    ), False, '', True
                ])

        # dungeon bin entries at the end:
        for i, name in enumerate(self.list_of_wtes_dungeon_bin):
            wtu_name = name[:-3] + WTU_FILE_EXT
            if name[:-3] + WTU_FILE_EXT not in self.list_of_wtus_dungeon_bin:
                wtu_name = None
            self._tree_level_dungeon_iter[name] = item_store.append(root, [
                'skytemple-e-graphics-symbolic', 'dungeon.bin:' + name, self,  WteWtuController, WteOpenSpec(
                    name, wtu_name, True
                ), False, '', True
            ])
            
        # zmappat at the end:
        for i, name in enumerate(self.list_of_zmappats_dungeon_bin):
            self._tree_level_dungeon_iter[name] = item_store.append(root, [
                'skytemple-e-graphics-symbolic', 'dungeon.bin:' + name, self,  ZMappaTController, name, False, '', True
            ])

        recursive_generate_item_store_row_label(self._tree_model[root])

    def mark_w16_as_modified(self, item_id):
        """Mark a specific w16 as modified"""
        w16_filename = self.list_of_w16s[item_id]
        self.project.mark_as_modified(w16_filename)
        # Mark as modified in tree
        row = self._tree_model[self._tree_level_iter[w16_filename]]
        recursive_up_item_store_mark_as_modified(row)

    def get_w16(self, item_id):
        w16_filename = self.list_of_w16s[item_id]
        return self.project.open_file_in_rom(w16_filename, FileType.W16)

    def get_wte(self, fn) -> Wte:
        return self.project.open_file_in_rom(fn, FileType.WTE)

    def get_wtu(self, fn) -> Wtu:
        return self.project.open_file_in_rom(fn, FileType.WTU)

    def get_dungeon_bin_file(self, fn):
        return self.dungeon_bin.get(fn)

    def mark_zmappat_as_modified(self, zmappat, fn):
        self.dungeon_bin.set(fn, zmappat)
        self.project.mark_as_modified(DUNGEON_BIN_PATH)
        # Mark as modified in tree
        row = self._tree_model[self._tree_level_dungeon_iter[fn]]
        recursive_up_item_store_mark_as_modified(row)
        
    def mark_wte_as_modified(self, item: WteOpenSpec, wte, wtu):
        if item.in_dungeon_bin:
            self.dungeon_bin.set(item.wte_filename, wte)
            if item.wtu_filename:
                self.dungeon_bin.set(item.wtu_filename, wtu)
            self.project.mark_as_modified(DUNGEON_BIN_PATH)
            # Mark as modified in tree
            row = self._tree_model[self._tree_level_dungeon_iter[item.wte_filename]]
            recursive_up_item_store_mark_as_modified(row)
        else:
            self.project.mark_as_modified(item.wte_filename)
            if item.wtu_filename:
                self.project.mark_as_modified(item.wtu_filename)
            # Mark as modified in tree
            row = self._tree_model[self._tree_level_iter[item.wte_filename]]
            recursive_up_item_store_mark_as_modified(row)
