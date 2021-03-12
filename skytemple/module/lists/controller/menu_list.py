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
from skytemple.controller.main import MainController
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.string_provider import StringType
from skytemple_files.hardcoded.menus import MenuEntry, MenuType
from skytemple_files.common.i18n_util import _

if TYPE_CHECKING:
    from skytemple.module.lists.module import ListsModule

PATTERN_ITEM_ENTRY = re.compile(r'.*\(#(\d+)\).*')
logger = logging.getLogger(__name__)


class MenuListController(AbstractController):
    def __init__(self, module: 'ListsModule', *args):
        super().__init__(module, *args)
        self.module = module
        self._string_provider = module.project.get_string_provider()

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'menu_list.glade')
        lst: Gtk.Box = self.builder.get_object('box_list')
        self._rank_up_table = self.module.get_rank_list()

        self._init_combos()
        self.on_lang_changed()
        self.builder.connect_signals(self)
        return lst

    def _init_combos(self):
        # Init available menus
        cb_store: Gtk.ListStore = self.builder.get_object('cb_store_menu')
        cb: Gtk.ComboBoxText = self.builder.get_object('cb_menu')
        # Init combobox
        cb_store.clear()
        for v in sorted(MenuType, key=lambda x:x.menu_name):
            cb_store.append([v.value, v.menu_name])
        cb.set_active(0)
        
        # Init available languages
        cb_store: Gtk.ListStore = self.builder.get_object('cb_store_lang')
        cb: Gtk.ComboBoxText = self.builder.get_object('cb_lang')
        # Init combobox
        cb_store.clear()
        for lang in self._string_provider.get_languages():
            cb_store.append([lang.locale, lang.name_localized])
        cb.set_active(0)
    
    def _get_current_settings(self) -> int:
        cb_store: Gtk.ListStore = self.builder.get_object('cb_store_menu')
        cb: Gtk.ComboBoxText = self.builder.get_object('cb_menu')

        return cb_store[cb.get_active_iter()][0]

    def on_btn_help_clicked(self, *args):
        md = SkyTempleMessageDialog(MainController.window(),
                                    Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                    Gtk.ButtonsType.OK,
                                    _("Menus are hardcoded so you can't add any option, but you can edit a few things.\n"
                                      "However, there are some rules: \n"
                                      " - Only the Game Main & Sub menus can have descriptions. \n"
                                      " - The action code tells the game what to do when selecting this menu. \n"
                                      "The meaning of the code values depends on the menu. \n"
                                      "It is also used to determine if a menu should be disabled (or hidden in the main menu).\n"
                                      " - The end of the menu is detected by the game with an entry in which the Name ID is set to 0. \n"
                                      "Also, the action code of that entry is used when pressing the B button (if the game allows it for this menu). \n"
                                      " - Editing a string with a specific ID will result of all strings using that ID to be changed."))
        md.run()
        md.destroy()

    def on_lang_changed(self, *args):
        cb_store: Gtk.ListStore = self.builder.get_object('cb_store_lang')
        cb: Gtk.ComboBoxText = self.builder.get_object('cb_lang')
        self._current_lang = cb_store[cb.get_active_iter()][0]
        self._refresh_list()
    
    def on_menu_changed(self, *args):
        self._refresh_list()

    def _regenerate_list(self):
        menu_id = self._get_current_settings()
        
        tree_store: Gtk.ListStore = self.builder.get_object('tree_store')
        new_list = []
        for row in tree_store:
            new_list.append(MenuEntry(row[0], row[2], row[4]))
        self.module.set_menu(menu_id, new_list)
        self._refresh_list()
        
    def on_id_name_edited(self, widget, path, text):
        try:
            tree_store: Gtk.ListStore = self.builder.get_object('tree_store')
            tree_store[path][0] = int(text)
        except ValueError:
            return
        
        self._regenerate_list()
        
    def on_id_description_edited(self, widget, path, text):
        try:
            tree_store: Gtk.ListStore = self.builder.get_object('tree_store')
            tree_store[path][2] = int(text)
        except ValueError:
            return
        
        self._regenerate_list()
        
    def on_action_edited(self, widget, path, text):
        try:
            tree_store: Gtk.ListStore = self.builder.get_object('tree_store')
            tree_store[path][4] = int(text)
        except ValueError:
            return
        
        self._regenerate_list()
    
    def on_string_name_edited(self, widget, path, text):
        
        tree_store: Gtk.ListStore = self.builder.get_object('tree_store')
        current_id = int(tree_store[path][0])
        if current_id>0:
            self._string_provider.get_model(self._current_lang).strings[
                current_id-1
            ] = text
            self._regenerate_list()
            self.module.mark_string_as_modified()
            
    def on_string_description_edited(self, widget, path, text):
        
        tree_store: Gtk.ListStore = self.builder.get_object('tree_store')
        current_id = int(tree_store[path][2])
        if current_id>0:
            self._string_provider.get_model(self._current_lang).strings[
                current_id-1
            ] = text
            self._regenerate_list()
            self.module.mark_string_as_modified()
    
    def _refresh_list(self):
        tree: Gtk.TreeView = self.builder.get_object('tree')
        self._list_store: Gtk.ListStore = tree.get_model()
        self._list_store.clear()

        # Iterate list
        menu_id = self._get_current_settings()
        menu_list = self.module.get_menu(menu_id)
        tree_store: Gtk.ListStore = self.builder.get_object('tree_store')
        tree_store.clear()
        str_list = self._string_provider.get_model(self._current_lang).strings
        for m in menu_list:
            if m.name_id>0:
                name = str_list[m.name_id-1]
            else:
                name = ""
            if m.description_id>0:
                description = str_list[m.description_id-1]
            else:
                description = ""
            tree_store.append([m.name_id, name, m.description_id, description, m.action])
