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
from skytemple.module.strings.controller.main import MainController, TEXT_STRINGS
from skytemple.module.strings.controller.strings import StringsController

from skytemple_files.common.types.file_types import FileType
from skytemple_files.list.actor.model import ActorListBin


class StringsModule(AbstractModule):
    """Module to edit the strings files in the MESSAGE directory."""
    @classmethod
    def depends_on(cls):
        return []

    @classmethod
    def sort_order(cls):
        return 30

    def __init__(self, rom_project: RomProject):
        self.project = rom_project

        self._tree_model = None
        self._tree_iters = {}

    def load_tree_items(self, item_store: TreeStore, root_node):
        root = item_store.append(root_node, [
            'skytemple-e-string-symbolic', TEXT_STRINGS, self, MainController, 0, False, '', True
        ])
        config = self.project.get_rom_module().get_static_data()
        for language in config.string_index_data.languages:
            self._tree_iters[language.filename] = item_store.append(root, [
                'skytemple-e-string-symbolic', language.name_localized, self, StringsController, language, False, '', True
            ])
        self._tree_model = item_store
        recursive_generate_item_store_row_label(self._tree_model[root])

    def get_string_file(self, filename: str) -> ActorListBin:
        return self.project.open_file_in_rom(f"MESSAGE/{filename}", FileType.STR)

    def mark_as_modified(self, filename: str):
        """Mark as modified"""
        self.project.mark_as_modified(f"MESSAGE/{filename}")
        # Mark as modified in tree
        row = self._tree_model[self._tree_iters[filename]]
        recursive_up_item_store_mark_as_modified(row)
