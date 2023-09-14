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
import logging
import re
from typing import TYPE_CHECKING, Optional, List, cast

from gi.repository import Gtk
from range_typed_integers import i16, i16_checked

from skytemple.core.module_controller import AbstractController
from skytemple.core.string_provider import StringType
from skytemple.core.ui_utils import glib_async, catch_overflow, builder_get_assert
from skytemple_files.common.i18n_util import _

if TYPE_CHECKING:
    from skytemple.module.lists.module import ListsModule

PATTERN_LOCATION_ENTRY = re.compile(r'.*\((\d+)\).*')
MOVE_NAME_PATTERN = re.compile(r'.*\((\d+)\).*')
logger = logging.getLogger(__name__)


class TacticsController(AbstractController):
    def __init__(self, module: 'ListsModule', item_id):
        super().__init__(module, item_id)
        self.module = module
        self._list: List[i16]
        self.builder: Gtk.Builder = None  # type: ignore

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'tactics.glade')
        lst = builder_get_assert(self.builder, Gtk.Box, 'box_list')
        self._list = self.module.get_tactics()
        self.refresh_list()

        self.builder.connect_signals(self)
        return lst

    @catch_overflow(i16)
    def on_cr_level_edited(self, widget, path, text):
        try:
            i16_checked(int(text))  # this is only for validating.
        except ValueError:
            return
        builder_get_assert(self.builder, Gtk.ListStore, 'list_store')[path][1] = text

    @glib_async
    def on_list_store_row_changed(self, store, path, l_iter):
        """Propagate changes to list store entries to the lists."""
        a_id, level, _ = store[path][:]
        a_id = int(a_id)
        self._list[a_id] = i16(int(level))

        self.module.set_tactics(self._list)

    def refresh_list(self):
        tree = builder_get_assert(self.builder, Gtk.TreeView, 'tree')
        store = cast(Gtk.ListStore, tree.get_model())
        if store:
            store.clear()

            # Iterate list
            for idx, entry in enumerate(self._list):
                store.append([
                    str(idx), str(entry), self.module.project.get_string_provider().get_value(
                        StringType.TACTICS_NAMES, idx
                    ) if idx != 11 else _('<Not working>')
                ])
