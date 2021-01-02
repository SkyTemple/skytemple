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
import logging
import re
from typing import TYPE_CHECKING, Optional, List

from gi.repository import Gtk

from skytemple.core.module_controller import AbstractController
from skytemple.core.string_provider import StringType
from skytemple_files.hardcoded.rank_up_table import Rank

if TYPE_CHECKING:
    from skytemple.module.lists.module import ListsModule

PATTERN_ITEM_ENTRY = re.compile(r'.*\(#(\d+)\).*')
logger = logging.getLogger(__name__)


class RankListController(AbstractController):
    def __init__(self, module: 'ListsModule', *args):
        super().__init__(module, *args)
        self.module = module
        self._rank_up_table: Optional[List[Rank]] = None
        self._item_names = {}
        self._list_store = None
        self._loading = True

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'rank_list.glade')
        lst: Gtk.Box = self.builder.get_object('box_list')
        self._rank_up_table = self.module.get_rank_list()

        self._init_item_store()
        self.refresh_list()
        self._loading = False
        self.builder.connect_signals(self)
        return lst

    def on_cr_rank_name_edited(self, widget, path, text):
        self._list_store[path][1] = text

    def on_cr_points_needed_next_edited(self, widget, path, text):
        try:
            int(text)
        except ValueError:
            return
        self._list_store[path][2] = text

    def on_cr_storage_capacity_edited(self, widget, path, text):
        try:
            int(text)
        except ValueError:
            return
        self._list_store[path][3] = text

    def on_cr_item_awarded_edited(self, widget, path, text):
        match = PATTERN_ITEM_ENTRY.match(text)
        if match is None:
            return
        try:
            item_id = int(match.group(1))
        except ValueError:
            return

        # item_id:
        self._list_store[path][4] = item_id
        # item_name:
        self._list_store[path][5] = self._item_names[item_id]

    def on_cr_item_awarded_editing_started(self, renderer, editable, path):
        editable.set_completion(self.builder.get_object('completion_items'))

    def on_list_store_row_changed(self, store, path, l_iter):
        """Propagate changes to list store entries to the lists."""
        if self._loading:
            return
        name_string_id, name_string, points_needed_next, storage_capacity, item_id, item_name, idx = store[path][:]
        self._rank_up_table[idx] = Rank(
            name_string_id, int(points_needed_next), int(storage_capacity), item_id
        )
        # Update the actual name_string
        sp = self.module.project.get_string_provider()
        sp.get_model().strings[
            sp.get_index(StringType.RANK_NAMES, idx)
        ] = name_string
        sp.mark_as_modified()
        logger.debug(f"Updated list entry {idx}: {self._rank_up_table[idx]}")

        self.module.set_rank_list(self._rank_up_table)

    def refresh_list(self):
        tree: Gtk.TreeView = self.builder.get_object('tree')
        self._list_store: Gtk.ListStore = tree.get_model()
        self._list_store.clear()

        # Iterate list
        sp = self.module.project.get_string_provider()
        for idx, rank_up in enumerate(self._rank_up_table):
            self._list_store.append([
                rank_up.rank_name_str, sp.get_value(StringType.RANK_NAMES, idx),
                str(rank_up.points_needed_next), str(rank_up.storage_capacity),
                rank_up.item_awarded, self._item_names[rank_up.item_awarded],
                idx
            ])

    def _init_item_store(self):
        item_store: Gtk.ListStore = self.builder.get_object('item_store')
        sp = self.module.project.get_string_provider()
        for i, name in enumerate(sp.get_all(StringType.ITEM_NAMES)):
            self._item_names[i] = f'{name} (#{i:03})'
            item_store.append([self._item_names[i]])
