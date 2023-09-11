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
from typing import TYPE_CHECKING, Dict, List, Optional, cast

from gi.repository import Gtk
from range_typed_integers import u8, u16, u16_checked, u8_checked

from skytemple.core.string_provider import StringType
from skytemple.core.ui_utils import glib_async, catch_overflow, builder_get_assert, assert_not_none
from skytemple.module.lists.controller.base import ListBaseController, PATTERN_MD_ENTRY
from skytemple_files.common.i18n_util import _
from skytemple_files.user_error import UserValueError

if TYPE_CHECKING:
    from skytemple.module.lists.module import ListsModule

PATTERN_LOCATION_ENTRY = re.compile(r'.*\((\d+)\).*')
logger = logging.getLogger(__name__)


class RecruitmentListController(ListBaseController):
    def __init__(self, module: 'ListsModule', *args):
        super().__init__(module, *args)
        self._species: List[u16]
        self._levels: List[u16]
        self._locations: List[u8]
        self._location_names: Dict[int, str] = {}
        self._list_store: Gtk.ListStore

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'recruitment_list.glade')
        lst = builder_get_assert(self.builder, Gtk.Box, 'box_list')
        self._species, self._levels, self._locations = self.module.get_recruitment_list()

        self._init_locations_store()
        self.load()
        return lst

    @catch_overflow(u16)
    def on_cr_level_edited(self, widget, path, text):
        try:
            u16_checked(int(text))  # this is only for validating.
        except ValueError:
            return
        self._list_store[path][1] = text

    @catch_overflow(u16)
    def on_cr_entity_edited(self, widget, path, text):
        match = PATTERN_MD_ENTRY.match(text)
        if match is None:
            return
        try:
            entid = u16_checked(int(match.group(1)))
        except ValueError:
            return
        idx = int(self._list_store[path][0])
        # ent_name:
        try:
            self._list_store[path][6] = self._ent_names[entid]
        except KeyError as e:
            raise UserValueError(_("No Pokémon with this ID found."))
        # entid:
        self._list_store[path][4] = entid
        # ent_icon:
        self._list_store[path][3] = self._get_icon(entid, idx, False)

    @catch_overflow(u8)
    def on_cr_location_edited(self, widget, path, text):
        match = PATTERN_LOCATION_ENTRY.match(text)
        if match is None:
            return
        try:
            location_id = u8_checked(int(match.group(1)))
        except ValueError:
            return

        # location_id:
        self._list_store[path][2] = str(location_id)
        # ent_name:
        self._list_store[path][5] = self._location_names[location_id]

    def on_completion_locations_match_selected(self, completion, model, tree_iter):
        pass

    def on_cr_location_editing_started(self, renderer, editable, path):
        editable.set_completion(builder_get_assert(self.builder, Gtk.EntryCompletion, 'completion_locations'))

    @glib_async
    def on_list_store_row_changed(self, store, path, l_iter):
        """Propagate changes to list store entries to the lists."""
        if self._loading:
            return
        a_id, level, location_id, ent_icon, entid, location_name, ent_name = store[path][:]
        a_id = int(a_id)
        self._species[a_id] = u16(int(entid))
        self._levels[a_id] = u16(int(level))
        self._locations[a_id] = u8(int(location_id))
        logger.debug(f"Updated list entry {a_id}: {entid}, {level}, {location_id}")

        self.module.set_recruitment_list(self._species, self._levels, self._locations)

    def refresh_list(self):
        tree: Gtk.TreeView = self.get_tree()
        self._list_store = assert_not_none(cast(Optional[Gtk.ListStore], tree.get_model()))
        self._list_store.clear()

        # Iterate list
        for idx, (e_species, e_level, e_location) in enumerate(zip(self._species, self._levels, self._locations)):
            self._list_store.append([
                str(idx), str(e_level), str(e_location), self._get_icon(e_species, idx, False),
                e_species, self._location_names[e_location], self._ent_names[e_species]
            ])

    def _init_locations_store(self):
        locations_store = builder_get_assert(self.builder, Gtk.ListStore, 'location_store')
        for idx in range(0, 256):
            name = self.module.project.get_string_provider().get_value(StringType.DUNGEON_NAMES_SELECTION, idx)
            self._location_names[idx] = f'{name} ({idx:04})'
            locations_store.append([self._location_names[idx]])

    def get_tree(self):
        return builder_get_assert(self.builder, Gtk.TreeView, 'tree')

    def can_be_placeholder(self):
        return False
