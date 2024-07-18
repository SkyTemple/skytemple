#  Copyright 2020-2024 Capypara and the SkyTemple Contributors
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
from __future__ import annotations
from typing import Optional

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.item_tree import (
    ItemTree,
    ItemTreeEntry,
    ItemTreeEntryRef,
    RecursionType,
)
from skytemple.core.rom_project import RomProject
from skytemple.module.symbols.widget.main import StSymbolsMainPage
from skytemple_files.common.i18n_util import _


class SymbolsModule(AbstractModule):
    # A reference to the item tree where this module's option is listed, or None if load_tree_items hasn't
    # been called yet.
    item_tree: Optional[ItemTree]
    # Current item tree entry, or None if load_tree_items hasn't been called yet.
    item_tree_entry: Optional[ItemTreeEntryRef]

    @classmethod
    def depends_on(cls):
        return []

    @classmethod
    def sort_order(cls):
        return 850

    def __init__(self, rom_project: RomProject):
        self.project = rom_project
        self.item_tree = None
        self.item_tree_entry = None

    def load_tree_items(self, item_tree: ItemTree):
        self.item_tree = item_tree
        self.item_tree_entry = item_tree.add_entry(
            None,
            ItemTreeEntry(
                icon="skytemple-e-patch-symbolic",
                name=_("Symbols"),
                module=self,
                view_class=StSymbolsMainPage,
                item_data=None,
            ),
        )

    def graphical_mark_as_modified(self):
        """
        Graphically displays the "unsaved changes" asterisk on the left menu. Should be called after changes have
        been made to the data handled by this module.
        Requires that load_tree_items() has been called first.
        :raises RuntimeError If this method is called fefore load_tree_items().
        """
        if self.item_tree is None or self.item_tree_entry is None:
            raise RuntimeError(
                "Cannot mark as modified before tree items are initialized. Call load_tree_items() first."
            )
        else:
            self.item_tree.mark_as_modified(self.item_tree_entry, RecursionType.UP)
