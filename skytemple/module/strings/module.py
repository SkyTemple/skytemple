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
from typing import Dict, Optional, Union

from gi.repository import Gtk
from skytemple.core.abstract_module import AbstractModule, DebuggingInfo
from skytemple.core.item_tree import ItemTree, ItemTreeEntry, ItemTreeEntryRef, RecursionType
from skytemple.core.module_controller import AbstractController
from skytemple.core.rom_project import RomProject
from skytemple.module.strings.controller.main import MainController, TEXT_STRINGS
from skytemple.module.strings.controller.strings import StringsController

from skytemple_files.common.types.file_types import FileType
from skytemple_files.data.str.model import Str


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

        self._item_tree: Optional[ItemTree] = None
        self._tree_iters: Dict[str, ItemTreeEntryRef] = {}

    def load_tree_items(self, item_tree: ItemTree):
        root = item_tree.add_entry(None, ItemTreeEntry(
            icon='skytemple-e-string-symbolic',
            name=TEXT_STRINGS,
            module=self,
            view_class=MainController,
            item_data=0
        ))
        config = self.project.get_rom_module().get_static_data()
        for language in config.string_index_data.languages:
            self._tree_iters[language.filename] = item_tree.add_entry(root, ItemTreeEntry(
                icon='skytemple-e-string-symbolic',
                name=language.name_localized,
                module=self,
                view_class=StringsController,
                item_data=language
            ))
        self._item_tree = item_tree

    def get_string_file(self, filename: str) -> Str:
        return self.project.open_file_in_rom(f"MESSAGE/{filename}", FileType.STR)

    def mark_as_modified(self, filename: str):
        """Mark as modified"""
        self.project.mark_as_modified(f"MESSAGE/{filename}")
        # Mark as modified in tree
        if self._item_tree is not None:
            self._item_tree.mark_as_modified(self._tree_iters[filename], RecursionType.UP)

    def collect_debugging_info(self, open_view: Union[AbstractController, Gtk.Widget]) -> Optional[DebuggingInfo]:
        if isinstance(open_view, StringsController):
            pass  # todo
        return None
