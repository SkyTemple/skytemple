#  Copyright 2020 Parakoopa
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
from typing import TYPE_CHECKING

from gi.repository import Gtk

from skytemple.core.module_controller import AbstractController
from skytemple.core.string_provider import StringType

if TYPE_CHECKING:
    from skytemple.module.dungeon.module import DungeonModule, DungeonViewInfo


class DungeonController(AbstractController):
    def __init__(self, module: 'DungeonModule', dungeon_info: 'DungeonViewInfo'):
        self.module = module
        self.dungeon_info = dungeon_info
        self.dungeon_name = self.module.project.get_string_provider().get_value(
            StringType.DUNGEON_NAMES_MAIN, self.dungeon_info.dungeon_id
        )

        self.builder = None
        self._is_loading = True

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'dungeon.glade')

        self.builder.get_object('label_dungeon_name').set_text(self.dungeon_name)
        edit_text = ''
        if not self.dungeon_info.length_can_be_edited:
            edit_text = '\nSince this is a Dojo Dungeon, the floor count can not be changed.'
            self.builder.get_object('edit_floor_count').set_sensitive(False)
        self.builder.get_object('label_floor_count').set_text(
            f'This dungeon has {self.module.get_number_floors(self.dungeon_info.dungeon_id)} floors.{edit_text}'
        )

        self._init_names()
        self._is_loading = False
        self.builder.connect_signals(self)

        return self.builder.get_object('main_box')

    def _init_names(self):
        sp = self.module.project.get_string_provider()
        langs = sp.get_languages()
        for lang_id in range(0, 5):
            label_lang: Gtk.Entry = self.builder.get_object(f'label_lang{lang_id}')
            entry_main_lang: Gtk.Entry = self.builder.get_object(f'entry_main_lang{lang_id}')
            entry_selection_lang: Gtk.Entry = self.builder.get_object(f'entry_selection_lang{lang_id}')
            entry_script_engine_lang: Gtk.Entry = self.builder.get_object(f'entry_script_engine_lang{lang_id}')
            entry_banner_lang: Gtk.Entry = self.builder.get_object(f'entry_banner_lang{lang_id}')
            if lang_id < len(langs):
                # We have this language
                lang = langs[lang_id]
                label_lang.set_text(lang.name)
                entry_main_lang.set_text(
                    sp.get_value(StringType.DUNGEON_NAMES_MAIN, self.dungeon_info.dungeon_id, langs[lang_id]).replace('\n', '\\n')
                )
                entry_selection_lang.set_text(
                    sp.get_value(StringType.DUNGEON_NAMES_SELECTION, self.dungeon_info.dungeon_id, langs[lang_id]).replace('\n', '\\n')
                )
                entry_script_engine_lang.set_text(
                    sp.get_value(StringType.DUNGEON_NAMES_SET_DUNGEON_BANNER, self.dungeon_info.dungeon_id, langs[lang_id]).replace('\n', '\\n')
                )
                entry_banner_lang.set_text(
                    sp.get_value(StringType.DUNGEON_NAMES_BANNER, self.dungeon_info.dungeon_id, langs[lang_id]).replace('\n', '\\n')
                )
                entry_main_lang.set_sensitive(True)
                entry_selection_lang.set_sensitive(True)
                entry_script_engine_lang.set_sensitive(True)
                entry_banner_lang.set_sensitive(True)

    def on_edit_floor_count_clicked(self, *args):
        pass  # todo

    def on_entry_main_lang0_changed(self, entry: Gtk.Entry):
        # TODO: Also update the Dungeon name in the item view
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_MAIN, 0)
        self.mark_as_modified()

    def on_entry_main_lang1_changed(self, entry: Gtk.Entry):
        # TODO: Also update the Group name in the item view
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_MAIN, 1)
        self.mark_as_modified()

    def on_entry_main_lang2_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_MAIN, 2)
        self.mark_as_modified()

    def on_entry_main_lang3_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_MAIN, 3)
        self.mark_as_modified()

    def on_entry_main_lang4_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_MAIN, 4)
        self.mark_as_modified()

    def on_entry_selection_lang0_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_SELECTION, 0)
        self.mark_as_modified()

    def on_entry_selection_lang1_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_SELECTION, 1)
        self.mark_as_modified()

    def on_entry_selection_lang2_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_SELECTION, 2)
        self.mark_as_modified()

    def on_entry_selection_lang3_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_SELECTION, 3)
        self.mark_as_modified()

    def on_entry_selection_lang4_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_SELECTION, 4)
        self.mark_as_modified()

    def on_entry_script_engine_lang0_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_SET_DUNGEON_BANNER, 0)
        self.mark_as_modified()

    def on_entry_script_engine_lang1_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_SET_DUNGEON_BANNER, 1)
        self.mark_as_modified()

    def on_entry_script_engine_lang2_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_SET_DUNGEON_BANNER, 2)
        self.mark_as_modified()

    def on_entry_script_engine_lang3_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_SET_DUNGEON_BANNER, 3)
        self.mark_as_modified()

    def on_entry_script_engine_lang4_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_SET_DUNGEON_BANNER, 4)
        self.mark_as_modified()

    def on_entry_banner_lang0_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_BANNER, 0)
        self.mark_as_modified()

    def on_entry_banner_lang1_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_BANNER, 1)
        self.mark_as_modified()

    def on_entry_banner_lang2_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_BANNER, 2)
        self.mark_as_modified()

    def on_entry_banner_lang3_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_BANNER, 3)
        self.mark_as_modified()

    def on_entry_banner_lang4_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_BANNER, 4)
        self.mark_as_modified()

    def mark_as_modified(self):
        if not self._is_loading:
            self.module.mark_dungeon_as_modified(self.dungeon_info.dungeon_id, False)

    def _update_lang_from_entry(self, w: Gtk.Entry, string_type, lang_index):
        if not self._is_loading:
            sp = self.module.project.get_string_provider()
            lang = sp.get_languages()[lang_index]
            sp.get_model(lang).strings[
                sp.get_index(string_type, self.dungeon_info.dungeon_id)
            ] = w.get_text()
