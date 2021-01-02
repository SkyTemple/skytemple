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
from skytemple.core.ui_utils import recursive_generate_item_store_row_label, recursive_up_item_store_mark_as_modified
from skytemple.module.bgp.controller.bgp import BgpController
from skytemple.module.bgp.controller.main import MainController, BACKGROUNDS_NAME
from skytemple_files.common.types.file_types import FileType

BGP_FILE_EXT = 'bgp'


class BgpModule(AbstractModule):
    @classmethod
    def depends_on(cls):
        return []

    @classmethod
    def sort_order(cls):
        return 150

    def __init__(self, rom_project: RomProject):
        """Loads the list of backgrounds for the ROM."""
        self.project = rom_project
        self.list_of_bgps = self.project.get_files_with_ext(BGP_FILE_EXT)

        self._tree_model = None
        self._tree_level_iter = []

    def load_tree_items(self, item_store: TreeStore, root_node):
        root = item_store.append(root_node, [
            'skytemple-e-bgp-symbolic', BACKGROUNDS_NAME, self, MainController, 0, False, '', True
        ])
        self._tree_model = item_store
        self._tree_level_iter = []
        for i, bgp_name in enumerate(self.list_of_bgps):
            self._tree_level_iter.append(
                item_store.append(root, [
                    'skytemple-e-bgp-symbolic', bgp_name, self,  BgpController, i, False, '', True
                ])
            )

        recursive_generate_item_store_row_label(self._tree_model[root])

    def mark_as_modified(self, item_id):
        """Mark a specific bg as modified"""
        bgp_filename = self.list_of_bgps[item_id]
        self.project.mark_as_modified(bgp_filename)
        # Mark as modified in tree
        row = self._tree_model[self._tree_level_iter[item_id]]
        recursive_up_item_store_mark_as_modified(row)

    def get_bgp(self, item_id):
        bgp_filename = self.list_of_bgps[item_id]
        return self.project.open_file_in_rom(bgp_filename, FileType.BGP)
