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
from typing import TYPE_CHECKING, cast
from gi.repository import Gtk
from range_typed_integers import i16, i16_checked
from skytemple.core.string_provider import StringType
from skytemple.core.ui_utils import glib_async, catch_overflow, data_dir
from skytemple_files.common.i18n_util import _

from skytemple.init_locale import LocalePatchedGtkTemplate

if TYPE_CHECKING:
    from skytemple.module.lists.module import ListsModule
PATTERN_LOCATION_ENTRY = re.compile(".*\\((\\d+)\\).*")
MOVE_NAME_PATTERN = re.compile(".*\\((\\d+)\\).*")
logger = logging.getLogger(__name__)
import os


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "lists", "tactics.ui"))
class StListsTacticsPage(Gtk.Box):
    __gtype_name__ = "StListsTacticsPage"
    module: ListsModule
    item_data: None
    list_store: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    tree: Gtk.TreeView = cast(Gtk.TreeView, Gtk.Template.Child())
    cr_level: Gtk.CellRendererText = cast(Gtk.CellRendererText, Gtk.Template.Child())

    def __init__(self, module: ListsModule, item_data: None):
        super().__init__()
        self.module = module
        self.item_data = item_data
        self._list: list[i16]
        self._list = self.module.get_tactics()
        self.refresh_list()

    @Gtk.Template.Callback()
    @catch_overflow(i16)
    def on_cr_level_edited(self, widget, path, text):
        try:
            i16_checked(int(text))  # this is only for validating.
        except ValueError:
            return
        self.list_store[path][1] = text

    @Gtk.Template.Callback()
    @glib_async
    def on_list_store_row_changed(self, store, path, l_iter):
        """Propagate changes to list store entries to the lists."""
        a_id, level, _ = store[path][:]
        a_id = int(a_id)
        self._list[a_id] = i16(int(level))
        self.module.set_tactics(self._list)

    def refresh_list(self):
        tree = self.tree
        store = cast(Gtk.ListStore, tree.get_model())
        if store:
            store.clear()
            # Iterate list
            for idx, entry in enumerate(self._list):
                store.append(
                    [
                        str(idx),
                        str(entry),
                        self.module.project.get_string_provider().get_value(StringType.TACTICS_NAMES, idx)
                        if idx != 11
                        else _("<Not working>"),
                    ]
                )
