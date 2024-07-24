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
from skytemple.core.ui_utils import glib_async, data_dir
from skytemple_files.common.i18n_util import _
from skytemple_files.hardcoded.dungeon_music import DungeonMusicEntry

from skytemple.init_locale import LocalePatchedGtkTemplate

if TYPE_CHECKING:
    from skytemple.module.lists.module import ListsModule
PATTERN_ITEM_ENTRY = re.compile(".*\\(#(\\d+)\\).*")
logger = logging.getLogger(__name__)
import os


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "lists", "dungeon_music.ui"))
class StListsDungeonMusicPage(Gtk.Box):
    __gtype_name__ = "StListsDungeonMusicPage"
    module: ListsModule
    item_data: None
    store_random_tracks: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    store_track_name: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    store_track_name_single: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    store_tracks: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    nb_sl: Gtk.Notebook = cast(Gtk.Notebook, Gtk.Template.Child())
    tree_tracks: Gtk.TreeView = cast(Gtk.TreeView, Gtk.Template.Child())
    cr_tracks_track: Gtk.CellRendererCombo = cast(Gtk.CellRendererCombo, Gtk.Template.Child())
    tree_random_tracks: Gtk.TreeView = cast(Gtk.TreeView, Gtk.Template.Child())
    cr_random_track1: Gtk.CellRendererCombo = cast(Gtk.CellRendererCombo, Gtk.Template.Child())
    cr_random_track2: Gtk.CellRendererCombo = cast(Gtk.CellRendererCombo, Gtk.Template.Child())
    cr_random_track3: Gtk.CellRendererCombo = cast(Gtk.CellRendererCombo, Gtk.Template.Child())
    cr_random_track4: Gtk.CellRendererCombo = cast(Gtk.CellRendererCombo, Gtk.Template.Child())

    def __init__(self, module: ListsModule, item_data: None):
        super().__init__()
        self.module = module
        self.item_data = item_data
        self._suppress_signals = True
        self._string_provider = module.project.get_string_provider()
        self._music_list, self._random_list = self.module.get_dungeon_music_spec()
        self._init_cr_stores()
        self._init_values()
        self._suppress_signals = False

    @Gtk.Template.Callback()
    @glib_async
    def on_cr_tracks_track_changed(self, widget, path, new_iter, *args):
        if not self._suppress_signals:
            track_store = self.store_tracks
            cb_store = self.store_track_name
            track_store[path][1] = cb_store[new_iter][1]
            self._music_list[int(track_store[path][0])] = DungeonMusicEntry(
                None, cb_store[new_iter][0], cb_store[new_iter][2]
            )
            self.module.set_dungeon_music(self._music_list, self._random_list)

    @Gtk.Template.Callback()
    @glib_async
    def on_cr_random_track1_changed(self, store, path, new_iter):
        if not self._suppress_signals:
            track_store = self.store_random_tracks
            cb_store = self.store_track_name_single
            track_store[path][1] = cb_store[new_iter][1]
            t = self._random_list[int(track_store[path][0])]
            self._random_list[int(track_store[path][0])] = (
                cb_store[new_iter][0],
                t[1],
                t[2],
                t[3],
            )
            self.module.set_dungeon_music(self._music_list, self._random_list)

    @Gtk.Template.Callback()
    @glib_async
    def on_cr_random_track2_changed(self, widget, path, new_iter, *args):
        if not self._suppress_signals:
            track_store = self.store_random_tracks
            cb_store = self.store_track_name_single
            track_store[path][2] = cb_store[new_iter][1]
            t = self._random_list[int(track_store[path][0])]
            self._random_list[int(track_store[path][0])] = (
                t[0],
                cb_store[new_iter][0],
                t[2],
                t[3],
            )
            self.module.set_dungeon_music(self._music_list, self._random_list)

    @Gtk.Template.Callback()
    @glib_async
    def on_cr_random_track3_changed(self, widget, path, new_iter, *args):
        track_store = self.store_random_tracks
        cb_store = self.store_track_name_single
        track_store[path][3] = cb_store[new_iter][1]
        t = self._random_list[int(track_store[path][0])]
        self._random_list[int(track_store[path][0])] = (
            t[0],
            t[1],
            cb_store[new_iter][0],
            t[3],
        )
        self.module.set_dungeon_music(self._music_list, self._random_list)

    @Gtk.Template.Callback()
    @glib_async
    def on_cr_random_track4_changed(self, widget, path, new_iter, *args):
        if not self._suppress_signals:
            track_store = self.store_random_tracks
            cb_store = self.store_track_name_single
            track_store[path][4] = cb_store[new_iter][1]
            t = self._random_list[int(track_store[path][0])]
            self._random_list[int(track_store[path][0])] = (
                t[0],
                t[1],
                t[2],
                cb_store[new_iter][0],
            )
            self.module.set_dungeon_music(self._music_list, self._random_list)

    def _init_cr_stores(self):
        music_entries = self.module.project.get_rom_module().get_static_data().script_data.bgms__by_id
        cb_store = self.store_track_name
        cb_store.clear()
        cb_store.append([999, _("Invalid? (#999)"), False])
        for idx, track in music_entries.items():
            cb_store.append([idx, track.name + f" (#{idx:03})", False])
        for idx in range(0, 30):
            cb_store.append([idx, _("Random ") + str(idx), True])
        cb_store = self.store_track_name_single
        cb_store.clear()
        for idx, track in music_entries.items():
            cb_store.append([idx, track.name + f" (#{idx:03})"])

    def _init_values(self):
        music_entries = self.module.project.get_rom_module().get_static_data().script_data.bgms__by_id
        cb_store = self.store_tracks
        cb_store.clear()
        for idx, track in enumerate(self._music_list):
            if track.is_random_ref:
                name = _("Random ") + str(track.track_or_ref)
            elif track.track_or_ref == 999:
                name = _("Invalid? (#999)")
            elif track.track_or_ref >= len(music_entries):
                name = _("INVALID!!!") + f" (#{idx:03})"
            else:
                name = music_entries[track.track_or_ref].name + f" (#{track.track_or_ref:03})"
            cb_store.append([str(idx), name])
        cb_store = self.store_random_tracks
        cb_store.clear()
        for idx, (a, b, c, d) in enumerate(self._random_list):
            cb_store.append(
                [
                    str(idx),
                    music_entries[a].name + f" (#{a:03})",
                    music_entries[b].name + f" (#{b:03})",
                    music_entries[c].name + f" (#{c:03})",
                    music_entries[d].name + f" (#{d:03})",
                ]
            )
