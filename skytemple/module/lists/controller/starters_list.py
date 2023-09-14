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
from typing import TYPE_CHECKING, Optional, Dict, cast

from gi.repository import Gtk
from range_typed_integers import u8_checked, u8, u16, u16_checked

from skytemple.core.string_provider import StringType
from skytemple.core.ui_utils import catch_overflow, builder_get_assert, iter_tree_model
from skytemple.module.lists.controller.base import ListBaseController, PATTERN_MD_ENTRY
from skytemple_files.common.i18n_util import _
from skytemple_files.user_error import UserValueError

if TYPE_CHECKING:
    from skytemple.module.lists.module import ListsModule

logger = logging.getLogger(__name__)
NATURES_AND_GENDERS = [
    (_("Hardy"), _("Male")),
    (_("Hardy"), _("Female")),
    (_("Docile"), _("Male")),
    (_("Docile"), _("Female")),
    (_("Brave"), _("Male")),
    (_("Brave"), _("Female")),
    (_("Jolly"), _("Male")),
    (_("Jolly"), _("Female")),
    (_("Impish"), _("Male")),
    (_("Impish"), _("Female")),
    (_("Naive"), _("Male")),
    (_("Naive"), _("Female")),
    (_("Timid"), _("Male")),
    (_("Timid"), _("Female")),
    (_("Hasty"), _("Male")),
    (_("Hasty"), _("Female")),
    (_("Sassy"), _("Male")),
    (_("Sassy"), _("Female")),
    (_("Calm"), _("Male")),
    (_("Calm"), _("Female")),
    (_("Relaxed"), _("Male")),
    (_("Relaxed"), _("Female")),
    (_("Lonely"), _("Male")),
    (_("Lonely"), _("Female")),
    (_("Quirky"), _("Male")),
    (_("Quirky"), _("Female")),
    (_("Quiet"), _("Male")),
    (_("Quiet"), _("Female")),
    (_("Rash"), _("Male")),
    (_("Rash"), _("Female")),
    (_("Bold"), _("Male")),  # TRANSLATORS: Nature
    (_("Bold"), _("Female"))  # TRANSLATORS: Nature
]


class StartersListController(ListBaseController):
    def __init__(self, module: 'ListsModule', *args):
        super().__init__(module, *args)
        self._player, self._partner = self.module.get_starter_ids()
        self._default_player, self._default_partner = self.module.get_starter_default_ids()
        self._player_iters: Dict[int, Gtk.TreeIter] = {}
        self._partner_iters: Dict[int, Gtk.TreeIter] = {}
        self.string_provider = self.module.project.get_string_provider()

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'starters_list.glade')
        assert self.builder

        default_player_name = builder_get_assert(self.builder, Gtk.Entry, 'default_player_name')
        default_partner_name = builder_get_assert(self.builder, Gtk.Entry, 'default_partner_name')
        default_team_name = builder_get_assert(self.builder, Gtk.Entry, 'default_team_name')
        default_player_name.set_text(self.string_provider.get_value(StringType.DEFAULT_TEAM_NAMES, 0))
        default_partner_name.set_text(self.string_provider.get_value(StringType.DEFAULT_TEAM_NAMES, 1))
        default_team_name.set_text(self.string_provider.get_value(StringType.DEFAULT_TEAM_NAMES, 2))

        player_start_level = builder_get_assert(self.builder, Gtk.Entry, 'player_start_level')
        player_start_level.set_text(str(self.module.get_starter_level_player()))
        partner_start_level = builder_get_assert(self.builder, Gtk.Entry, 'partner_start_level')
        partner_start_level.set_text(str(self.module.get_starter_level_partner()))

        self.load()

        default_player_species = builder_get_assert(self.builder, Gtk.Entry, 'default_player_species')
        default_player_species.set_text(self._ent_names[self._default_player])
        default_partner_species = builder_get_assert(self.builder, Gtk.Entry, 'default_partner_species')
        default_partner_species.set_text(self._ent_names[self._default_partner])

        return builder_get_assert(self.builder, Gtk.Widget, 'box')

    @catch_overflow(u16)
    def on_default_player_species_changed(self, w, *args):
        match = PATTERN_MD_ENTRY.match(w.get_text())
        if match is None:
            return
        try:
            val = u16_checked(int(match.group(1)))
        except ValueError:
            return
        if self._default_player != val:
            self._default_player = val
            self.module.set_starter_default_ids(self._default_player, self._default_partner)

    @catch_overflow(u16)
    def on_default_partner_species_changed(self, w, *args):
        match = PATTERN_MD_ENTRY.match(w.get_text())
        if match is None:
            return
        try:
            val = u16_checked(int(match.group(1)))
        except ValueError:
            return
        if self._default_partner != val:
            self._default_partner = val
            self.module.set_starter_default_ids(self._default_player, self._default_partner)
    
    def on_default_player_name_changed(self, w: Gtk.Entry):
        for lang in self.string_provider.get_languages():
            self.string_provider.get_model(lang).strings[
                self.string_provider.get_index(StringType.DEFAULT_TEAM_NAMES, 0)
            ] = w.get_text()
        self.module.mark_str_as_modified()

    def on_default_partner_name_changed(self, w: Gtk.Entry):
        for lang in self.string_provider.get_languages():
            self.string_provider.get_model(lang).strings[
                self.string_provider.get_index(StringType.DEFAULT_TEAM_NAMES, 1)
            ] = w.get_text()
        self.module.mark_str_as_modified()

    def on_default_team_name_changed(self, w: Gtk.Entry):
        for lang in self.string_provider.get_languages():
            self.string_provider.get_model(lang).strings[
                self.string_provider.get_index(StringType.DEFAULT_TEAM_NAMES, 2)
            ] = w.get_text()
        self.module.mark_str_as_modified()

    @catch_overflow(u8)
    def on_player_start_level_changed(self, w: Gtk.Entry):
        try:
            val = u8_checked(int(w.get_text()))
        except ValueError:
            return
        self.module.set_starter_level_player(val)

    @catch_overflow(u8)
    def on_partner_start_level_changed(self, w: Gtk.Entry):
        try:
            val = u8_checked(int(w.get_text()))
        except ValueError:
            return
        self.module.set_starter_level_partner(val)

    def on_player_species_edited(self, widget, path, text):
        self._on_species_edited('player_list_store', self._player_iters, path, text)

    def on_partner_species_edited(self, widget, path, text):
        self._on_species_edited('partner_list_store', self._partner_iters, path, text)

    def _on_species_edited(self, store_name, iters, path, text):
        store = builder_get_assert(self.builder, Gtk.ListStore, store_name)
        match = PATTERN_MD_ENTRY.match(text)
        if match is None:
            return
        try:
            entid = int(match.group(1))
        except ValueError:
            return
        idx = int(store[path][0])
        # ent_name:
        try:
            store[path][3] = self._ent_names[entid]
        except KeyError as e:
            raise UserValueError(_("No Pokémon with this ID found."))
        # entid:
        store[path][2] = entid
        # ent_icon:
        # If color is orange it's special.
        store[path][1] = self._get_icon(entid, idx, False, store, iters)
        self._apply()

    def refresh_list(self):
        self._icon_pixbufs = {}
        # PLAYER LIST
        tree = builder_get_assert(self.builder, Gtk.TreeView, 'player_tree')
        store = cast(Optional[Gtk.ListStore], tree.get_model())
        assert store is not None
        store.clear()
        for idx, entry in enumerate(self._player):
            # todo
            l_iter = store.append([
                str(idx), self._get_icon(entry, idx, False, store, self._player_iters),
                entry, self._ent_names[entry], NATURES_AND_GENDERS[idx][0], NATURES_AND_GENDERS[idx][1]
            ])
            self._player_iters[idx] = l_iter

        # PARTNER LIST
        tree = builder_get_assert(self.builder, Gtk.TreeView, 'partner_tree')
        store = cast(Optional[Gtk.ListStore], tree.get_model())
        assert store is not None
        store.clear()
        for idx, entry in enumerate(self._partner):
            l_iter = store.append([
                str(idx), self._get_icon(entry, idx, False, store, self._player_iters),
                entry, self._ent_names[entry]
            ])
            self._partner_iters[idx] = l_iter

    def _apply(self):
        player_prep = {}
        partner_prep = {}
        for row in iter_tree_model(builder_get_assert(self.builder, Gtk.ListStore, 'player_list_store')):
            player_prep[int(row[0])] = row[2]
        for row in iter_tree_model(builder_get_assert(self.builder, Gtk.ListStore, 'partner_list_store')):
            partner_prep[int(row[0])] = row[2]
        player = [x[1] for x in sorted(player_prep.items(), key=lambda x: x[0])]
        partner = [x[1] for x in sorted(partner_prep.items(), key=lambda x: x[0])]
        self.module.set_starter_ids(player, partner)

    def get_tree(self):
        return [
            builder_get_assert(self.builder, Gtk.TreeView, 'player_tree'),
            builder_get_assert(self.builder, Gtk.TreeView, 'partner_tree'),
        ]

    def _get_store_icon_id(self):
        return 1

    def _get_store_entid_id(self):
        return 2

    def can_be_placeholder(self):
        return False
