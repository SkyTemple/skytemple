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

from gi.repository.Gtk import TreeStore

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.rom_project import RomProject
from skytemple.core.ui_utils import recursive_generate_item_store_row_label, recursive_up_item_store_mark_as_modified
from skytemple.module.misc_graphics.controller.w16 import W16Controller
from skytemple.module.misc_graphics.controller.main import MainController, MISC_GRAPHICS
from skytemple_files.common.types.file_types import FileType

W16_FILE_EXT = 'w16'


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

        self._tree_model = None
        self._tree_level_iter = []

    def load_tree_items(self, item_store: TreeStore, root_node):
        root = item_store.append(root_node, [
            'folder-pictures-symbolic', MISC_GRAPHICS, self, MainController, 0, False, '', True
        ])
        self._tree_model = item_store
        self._tree_level_iter = []
        for i, w16_name in enumerate(self.list_of_w16s):
            self._tree_level_iter.append(
                item_store.append(root, [
                    'image-x-generic-symbolic', w16_name, self,  W16Controller, i, False, '', True
                ])
            )

        recursive_generate_item_store_row_label(self._tree_model[root])

    def mark_w16_as_modified(self, item_id):
        """Mark a specific w16 as modified"""
        w16_filename = self.list_of_w16s[item_id]
        self.project.mark_as_modified(w16_filename)
        # Mark as modified in tree
        row = self._tree_model[self._tree_level_iter[item_id]]
        recursive_up_item_store_mark_as_modified(row)

    def get_w16(self, item_id):
        w16_filename = self.list_of_w16s[item_id]
        return self.project.open_file_in_rom(w16_filename, FileType.W16)
