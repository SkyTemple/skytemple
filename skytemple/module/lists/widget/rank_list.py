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
import logging
import re
from typing import TYPE_CHECKING, Optional, cast
from gi.repository import Gtk
from range_typed_integers import u32_checked, u32
from skytemple.core.string_provider import StringType
from skytemple.core.ui_utils import (
    glib_async,
    catch_overflow,
    assert_not_none,
    data_dir,
)
from skytemple_files.hardcoded.rank_up_table import Rank

from skytemple.init_locale import LocalePatchedGtkTemplate

if TYPE_CHECKING:
    from skytemple.module.lists.module import ListsModule
PATTERN_ITEM_ENTRY = re.compile(".*\\(#(\\d+)\\).*")
logger = logging.getLogger(__name__)
import os


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "lists", "rank_list.ui"))
class StListsRankListPage(Gtk.Box):
    __gtype_name__ = "StListsRankListPage"
    module: ListsModule
    item_data: None
    item_store: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    completion_items: Gtk.EntryCompletion = cast(Gtk.EntryCompletion, Gtk.Template.Child())
    list_store: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    tree: Gtk.TreeView = cast(Gtk.TreeView, Gtk.Template.Child())
    cr_rank_name: Gtk.CellRendererText = cast(Gtk.CellRendererText, Gtk.Template.Child())
    cr_points_needed_next: Gtk.CellRendererText = cast(Gtk.CellRendererText, Gtk.Template.Child())
    cr_storage_capacity: Gtk.CellRendererText = cast(Gtk.CellRendererText, Gtk.Template.Child())
    cr_item_awarded: Gtk.CellRendererText = cast(Gtk.CellRendererText, Gtk.Template.Child())

    def __init__(self, module: ListsModule, item_data: None):
        super().__init__()
        self.module = module
        self.item_data = item_data
        self._rank_up_table: list[Rank] = self.module.get_rank_list()
        self._item_names: dict[int, str] = {}
        self._list_store: Gtk.ListStore = None  # type: ignore
        self._loading = True
        self._init_item_store()
        self.refresh_list()
        self._loading = False

    @Gtk.Template.Callback()
    def on_cr_rank_name_edited(self, widget, path, text):
        self._list_store[path][1] = text

    @Gtk.Template.Callback()
    @catch_overflow(u32)
    def on_cr_points_needed_next_edited(self, widget, path, text):
        try:
            u32_checked(int(text))
        except ValueError:
            return
        self._list_store[path][2] = text

    @Gtk.Template.Callback()
    @catch_overflow(u32)
    def on_cr_storage_capacity_edited(self, widget, path, text):
        try:
            u32_checked(int(text))
        except ValueError:
            return
        self._list_store[path][3] = text

    @Gtk.Template.Callback()
    @catch_overflow(u32)
    def on_cr_item_awarded_edited(self, widget, path, text):
        match = PATTERN_ITEM_ENTRY.match(text)
        if match is None:
            return
        try:
            item_id = u32_checked(int(match.group(1)))
        except ValueError:
            return
        # item_id:
        self._list_store[path][4] = item_id
        # item_name:
        self._list_store[path][5] = self._item_names[item_id]

    @Gtk.Template.Callback()
    def on_cr_item_awarded_editing_started(self, renderer, editable, path):
        editable.set_completion(self.completion_items)

    @Gtk.Template.Callback()
    @glib_async
    def on_list_store_row_changed(self, store, path, l_iter):
        """Propagate changes to list store entries to the lists."""
        if self._loading:
            return
        (
            name_string_id,
            name_string,
            points_needed_next,
            storage_capacity,
            item_id,
            item_name,
            idx,
        ) = store[path][:]
        self._rank_up_table[idx] = Rank(
            u32(name_string_id),
            u32(int(points_needed_next)),
            u32(int(storage_capacity)),
            u32(item_id),
        )
        # Update the actual name_string
        sp = self.module.project.get_string_provider()
        sp.get_model().strings[sp.get_index(StringType.RANK_NAMES, idx)] = name_string
        sp.mark_as_modified()
        logger.debug(f"Updated list entry {idx}: {self._rank_up_table[idx]}")
        self.module.set_rank_list(self._rank_up_table)

    def refresh_list(self):
        tree = self.tree
        self._list_store = assert_not_none(cast(Optional[Gtk.ListStore], tree.get_model()))
        self._list_store.clear()
        # Iterate list
        sp = self.module.project.get_string_provider()
        for idx, rank_up in enumerate(self._rank_up_table):
            self._list_store.append(
                [
                    rank_up.rank_name_str,
                    sp.get_value(StringType.RANK_NAMES, idx),
                    str(rank_up.points_needed_next),
                    str(rank_up.storage_capacity),
                    rank_up.item_awarded,
                    self._item_names[rank_up.item_awarded],
                    idx,
                ]
            )

    def _init_item_store(self):
        item_store = self.item_store
        sp = self.module.project.get_string_provider()
        for i, name in enumerate(sp.get_all(StringType.ITEM_NAMES)):
            self._item_names[i] = f"{name} (#{i:03})"
            item_store.append([self._item_names[i]])
