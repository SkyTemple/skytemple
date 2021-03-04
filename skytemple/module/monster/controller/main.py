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
#  along with SkyTemple.  If not, see <https://www.gnu.org/licenses/>.

import re
from typing import TYPE_CHECKING, Tuple, List

from gi.repository import Gtk
from gi.repository.Gtk import Widget

from skytemple.core.string_provider import StringProvider, StringType
from skytemple.core.module_controller import AbstractController
from skytemple_files.data.tbl_talk import TBL_TALK_SPEC_LEN
from skytemple_files.data.tbl_talk.model import TalkType
from skytemple_files.common.i18n_util import f, _

if TYPE_CHECKING:
    from skytemple.module.monster.module import MonsterModule

MONSTER_NAME = 'Pokémon'
MAP_TALK_TYPE = [StringType.DIALOGUE_HEALTHY,
                 StringType.DIALOGUE_HALF_LIFE,
                 StringType.DIALOGUE_PINCH,
                 StringType.DIALOGUE_LEVEL_UP,
                 StringType.DIALOGUE_WAIT,
                 StringType.DIALOGUE_GROUND_WAIT]

# TODO: Static list of actors
UNIQUE_ACTORS = [_("Partner 1"),
                 _("Partner 2"),
                 _("Partner 3"),
                 _("Grovyle"),
                 _("Chatot"),
                 _("Bidoof"),
                 _("Celebi"),
                 _("Cresselia")]+[_("Unknown Actor %02d") % i for i in range(8, 13)]+[_("Shaymin"),
                 _("Snover"),
                 _("Armaldo"),
                 _("Banette"), #Not sure about those two (I could have swapped them)
                 _("Skorupi"), #With this
                 _("Medicham"),
                 _("Gardevoir"),
                 _("Unknown Actor 20"),
                 _("Celebi"),
                 _("Dusknoir"),
                 _("Dusknoir"),
                 _("Dusknoir"),
                 _("Dusknoir"),
                 _("Dusknoir"),
                 _("Dusknoir"),
                 _("Dusknoir")]+[_("Unknown Actor %02d") % i for i in range(29, 34)]+[_("Loudred"), _("Unknown Actor 35")]
class MainController(AbstractController):
    def __init__(self, module: 'MonsterModule', item_id: int):
        self.module = module
        self._string_provider = module.project.get_string_provider()

    def get_view(self) -> Widget:
        self.builder = self._get_builder(__file__, 'main.glade')
        self._init_combos()
        self._init_groups()
        self._init_spec_personalities()
        
        self.on_lang_changed()
        self.builder.connect_signals(self)
        return self.builder.get_object('box_list')

    def _init_groups(self):
        self.builder.get_object('spin_group_nb').set_text(str(0))
        self.builder.get_object('spin_group_nb').set_increments(1,1)
        self.builder.get_object('spin_group_nb').set_range(0, self.module.get_nb_personality_groups()-1)
        
    def _init_combos(self):
        # Init available types
        cb_store: Gtk.ListStore = self.builder.get_object('cb_store_types')
        cb: Gtk.ComboBoxText = self.builder.get_object('cb_types')
        # Init combobox
        cb_store.clear()
        for v in TalkType:
            cb_store.append([v.value, v.description])
        cb.set_active(0)
        
        # Init available languages
        cb_store: Gtk.ListStore = self.builder.get_object('cb_store_lang')
        cb: Gtk.ComboBoxText = self.builder.get_object('cb_lang')
        # Init combobox
        cb_store.clear()
        for lang in self._string_provider.get_languages():
            cb_store.append([lang.locale, lang.name])
        cb.set_active(0)

    def on_lang_changed(self, *args):
        cb_store: Gtk.ListStore = self.builder.get_object('cb_store_lang')
        cb: Gtk.ComboBoxText = self.builder.get_object('cb_lang')
        self._current_lang = cb_store[cb.get_active_iter()][0]
        self._refresh_list()


    def _init_spec_personalities(self):
        tree_store: Gtk.ListStore = self.builder.get_object('special_personalities_tree_store')
        tree_store.clear()
        for i in range(TBL_TALK_SPEC_LEN):
            tree_store.append([UNIQUE_ACTORS[i], self.module.get_special_personality(i)])
        
    def on_value_changed(self, *args):
        self._refresh_list()

    def _get_current_settings(self) -> Tuple[int, TalkType]:
        cb_store: Gtk.ListStore = self.builder.get_object('cb_store_types')
        cb: Gtk.ComboBoxText = self.builder.get_object('cb_types')

        talk_type: TalkType = TalkType(cb_store[cb.get_active_iter()][0])
        group: int = int(self.builder.get_object('spin_group_nb').get_text())
        return group, talk_type
        
    def _regenerate_list(self):
        group, talk_type = self._get_current_settings()
        
        tree_store: Gtk.ListStore = self.builder.get_object('group_text_tree_store')
        new_list = []
        for row in tree_store:
            new_list.append(row[0])
        self.module.set_personality_dialogues(group, talk_type, new_list)
        self.module.mark_tbl_talk_as_modified()
        self._refresh_list()
        
    def on_spec_personality_edited(self, widget, path, text):
        try:
            tree_store: Gtk.ListStore = self.builder.get_object('special_personalities_tree_store')
            tree_store[path][1] = int(text)
            self.module.set_special_personality(int(path), int(text))
        except ValueError:
            return
        
    def on_id_text_edited(self, widget, path, text):
        try:
            tree_store: Gtk.ListStore = self.builder.get_object('group_text_tree_store')
            tree_store[path][0] = int(text)
        except ValueError:
            return
        
        self._regenerate_list()
    
    def on_string_text_edited(self, widget, path, text):
        _, talk_type = self._get_current_settings()
        
        tree_store: Gtk.ListStore = self.builder.get_object('group_text_tree_store')
        self._string_provider.get_model(self._current_lang).strings[
            self._string_provider.get_index(MAP_TALK_TYPE[talk_type.value], int(tree_store[path][0]))
        ] = text
        self._regenerate_list()
        self.module.mark_string_as_modified()

    def on_btn_add_dialogue_clicked(self, *args):
        store: Gtk.ListStore = self.builder.get_object('group_text_tree_store')
        store.append([0, ""])
        self._regenerate_list()

    def on_btn_remove_dialogue_clicked(self, *args):
        # Deletes all selected dialogue entries
        # Allows multiple deletions
        active_rows : List[Gtk.TreePath] = self.builder.get_object('group_text_tree').get_selection().get_selected_rows()[1]
        store: Gtk.ListStore = self.builder.get_object('group_text_tree_store')
        for x in reversed(sorted(active_rows, key=lambda x:x.get_indices())):
            del store[x.get_indices()[0]]
        self._regenerate_list()
        
    def on_btn_add_group_clicked(self, *args):
        self.module.add_personality_group()
        self._init_groups()
        self.builder.get_object('spin_group_nb').set_text(str(self.module.get_nb_personality_groups()-1))
        self.module.mark_tbl_talk_as_modified()
        self._refresh_list()

    def on_btn_remove_group_clicked(self, *args):
        # Deletes current group
        if self.module.get_nb_personality_groups()>1:
            group, _ = self._get_current_settings()
            self.module.remove_personality_group(group)
            self._init_groups()
            self.builder.get_object('spin_group_nb').set_text(str(max(group-1, 0)))
            self.module.mark_tbl_talk_as_modified()
            self._refresh_list()
    
    def _refresh_list(self):
        group, talk_type = self._get_current_settings()
        dialogues: List[int] = self.module.get_personality_dialogues(group, talk_type)
        tree_store: Gtk.ListStore = self.builder.get_object('group_text_tree_store')
        tree_store.clear()
        for d in dialogues:
            tree_store.append([d, self._string_provider.get_value(MAP_TALK_TYPE[talk_type.value], d, self._current_lang)])
