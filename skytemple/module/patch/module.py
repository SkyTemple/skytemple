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
from skytemple.core.ui_utils import recursive_up_item_store_mark_as_modified, generate_item_store_row_label
from skytemple.module.patch.controller.main import MainController
from skytemple_files.common.i18n_util import _


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

        self._tree_model = None
        self._tree_iter = None

    def load_tree_items(self, item_store: TreeStore, root_node):
        self._tree_iter = item_store.append(root_node, [
            'skytemple-e-patch-symbolic', _('ASM Patches'), self, MainController, 0, False, '', True
        ])
        generate_item_store_row_label(item_store[self._tree_iter])
        self._tree_model = item_store

    def mark_as_modified(self):
        """Mark as modified"""
        # We don't have to mark anything at the project as modified, the
        # binaries are already patched.
        self.project.force_mark_as_modified()
        # Mark as modified in tree
        row = self._tree_model[self._tree_iter]
        recursive_up_item_store_mark_as_modified(row)
