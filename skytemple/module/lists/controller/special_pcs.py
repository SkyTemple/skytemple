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
from typing import TYPE_CHECKING, Dict, Optional, List, cast

from gi.repository import Gtk
from range_typed_integers import u16, u16_checked

from skytemple.core.string_provider import StringType
from skytemple.core.ui_utils import glib_async, catch_overflow, builder_get_assert, assert_not_none
from skytemple.module.lists.controller.base import ListBaseController, PATTERN_MD_ENTRY
from skytemple_files.hardcoded.default_starters import SpecialEpisodePc

if TYPE_CHECKING:
    from skytemple.module.lists.module import ListsModule

PATTERN_LOCATION_ENTRY = re.compile(r'.*\((\d+)\).*')
MOVE_NAME_PATTERN = re.compile(r'.*\((\d+)\).*')
logger = logging.getLogger(__name__)


class SpecialPcsController(ListBaseController):
    def __init__(self, module: 'ListsModule', *args):
        super().__init__(module, *args)
        self._list: List[SpecialEpisodePc]
        self._list_store: Gtk.ListStore
        self._location_names: Dict[int, str] = {}
        self.move_entries = self.module.get_waza_p().moves

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'special_pcs.glade')
        lst = builder_get_assert(self.builder, Gtk.Box, 'box_list')
        self._list = self.module.get_special_pcs()

        self._init_completions()
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
    def on_cr_iq_edited(self, widget, path, text):
        try:
            u16_checked(int(text))  # this is only for validating.
        except ValueError:
            return
        self._list_store[path][12] = text

    def on_cr_do_not_fix_entire_moveset_toggled(self, widget, path):
        self._list_store[path][11] = not widget.get_active()

    @catch_overflow(u16)
    def on_cr_fixed_hp_edited(self, widget, path, text):
        try:
            u16_checked(int(text))  # this is only for validating.
        except ValueError:
            return
        self._list_store[path][13] = text

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

        # entid:
        self._list_store[path][4] = entid
        # ent_icon:
        self._list_store[path][3] = self._get_icon(entid, idx, False)
        # ent_name:
        self._list_store[path][6] = self._ent_names[entid]

    @catch_overflow(u16)
    def on_cr_location_edited(self, widget, path, text):
        match = PATTERN_LOCATION_ENTRY.match(text)
        if match is None:
            return
        try:
            location_id = u16_checked(int(match.group(1)))
        except ValueError:
            return

        # location_id:
        self._list_store[path][2] = str(location_id)
        # ent_name:
        self._list_store[path][5] = self._location_names[location_id]

    @catch_overflow(u16)
    def on_cr_move1_edited(self, widget, path, text):
        self._update_move(path, text, 7)

    @catch_overflow(u16)
    def on_cr_move2_edited(self, widget, path, text):
        self._update_move(path, text, 8)

    @catch_overflow(u16)
    def on_cr_move3_edited(self, widget, path, text):
        self._update_move(path, text, 9)

    @catch_overflow(u16)
    def on_cr_move4_edited(self, widget, path, text):
        self._update_move(path, text, 10)

    def on_cr_move_editing_started(self, renderer, editable, path):
        editable.set_completion(builder_get_assert(self.builder, Gtk.ListStore, 'completion_moves'))

    def on_cr_location_editing_started(self, renderer, editable, path):
        editable.set_completion(builder_get_assert(self.builder, Gtk.EntryCompletion, 'completion_locations'))

    @glib_async
    def on_list_store_row_changed(self, store, path, l_iter):
        """Propagate changes to list store entries to the lists."""
        if self._loading:
            return
        a_id, level, location_id, ent_icon, entid, location_name, ent_name, \
            move1, move2, move3, move4, unk_e, iq, unk12 = store[path][:]
        a_id = int(a_id)
        self._list[a_id] = SpecialEpisodePc(
            u16(int(entid)), u16(int(location_id)),
            u16(self._get_move_id_from_display_name(move1)), u16(self._get_move_id_from_display_name(move2)),
            u16(self._get_move_id_from_display_name(move3)), u16(self._get_move_id_from_display_name(move4)),
            int(unk_e) > 0, u16(int(level)), u16(int(iq)), u16(int(unk12))
        )

        self.module.set_special_pcs(self._list)

    def refresh_list(self):
        tree: Gtk.TreeView = self.get_tree()
        self._list_store = assert_not_none(cast(Optional[Gtk.ListStore], tree.get_model()))
        self._list_store.clear()

        # Iterate list
        for idx, entry in enumerate(self._list):
            self._list_store.append([
                str(idx), str(entry.level), str(entry.joined_at), self._get_icon(entry.poke_id, idx, False),
                entry.poke_id, self._location_names[entry.joined_at], self._ent_names[entry.poke_id],
                self._get_move_display_name(entry.move1), self._get_move_display_name(entry.move2),
                self._get_move_display_name(entry.move3), self._get_move_display_name(entry.move4),
                bool(entry.do_not_fix_entire_moveset), str(entry.iq), str(entry.fixed_hp)
            ])

    def _update_move(self, path, text, value_pos: int):
        try:
            u16_checked(self._get_move_id_from_display_name(text))
        except ValueError:
            return
        self._list_store[path][value_pos] = text

    def _init_completions(self):
        locations_store = builder_get_assert(self.builder, Gtk.ListStore, 'location_store')
        for idx in range(0, 256):
            name = self.module.project.get_string_provider().get_value(StringType.DUNGEON_NAMES_SELECTION, idx)
            self._location_names[idx] = f'{name} ({idx:04})'
            locations_store.append([self._location_names[idx]])

        store = builder_get_assert(self.builder, Gtk.ListStore, 'store_completion_moves')
        for i in range(len(self.move_entries)):
            store.append([self._get_move_display_name(i)])

    def _get_move_display_name(self, i: int):
        name = self.module.project.get_string_provider().get_value(StringType.MOVE_NAMES, i)
        return f'{name} ({i:03})'

    def _get_move_id_from_display_name(self, display_name):
        match = MOVE_NAME_PATTERN.match(display_name)
        if match is None:
            raise ValueError
        return int(match.group(1))

    def get_tree(self):
        return builder_get_assert(self.builder, Gtk.TreeView, 'tree')

    def can_be_placeholder(self):
        return False
