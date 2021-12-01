#  Copyright 2020-2021 Capypara and the SkyTemple Contributors
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
import sys
from typing import TYPE_CHECKING, Optional, List

from gi.repository import Gtk

from skytemple.core.error_handler import display_error
from skytemple.core.module_controller import AbstractController
from skytemple.controller.main import MainController
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.string_provider import StringType
from skytemple_files.common.i18n_util import _

if TYPE_CHECKING:
    from skytemple.module.moves_items.module import MovesItemsModule

PATTERN_ITEM_ENTRY = re.compile(r'.*\(#(\d+)\).*')
logger = logging.getLogger(__name__)


class ItemKeysController(AbstractController):
    def __init__(self, module: 'MovesItemsModule', *args):
        super().__init__(module, *args)
        self.module = module
        self._string_provider = module.project.get_string_provider()

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'item_keys.glade')
        lst: Gtk.Box = self.builder.get_object('box_list')

        self._init_combos()
        self.on_lang_changed()
        self.builder.connect_signals(self)
        return lst

    def _init_combos(self):
        # Init available languages
        cb_store: Gtk.ListStore = self.builder.get_object('cb_store_lang')
        cb: Gtk.ComboBoxText = self.builder.get_object('cb_lang')
        # Init combobox
        cb_store.clear()
        for lang in self._string_provider.get_languages():
            cb_store.append([lang.locale, lang.name_localized])
        cb.set_active(0)


    def on_btn_help_clicked(self, *args):
        md = SkyTempleMessageDialog(MainController.window(),
                                    Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                    Gtk.ButtonsType.OK,
                                    _("""Sort keys are used to sort items in your inventory when using the sort feature in game.
The game sorts items starting from the one with the lowest key to the highest.
Several items can have the same key; this means they will be mixed together while sorting (e.g. Lookalike items).
Only keys from 0 to 2047 should be used."""))
        md.run()
        md.destroy()

    def on_lang_changed(self, *args):
        cb_store: Gtk.ListStore = self.builder.get_object('cb_store_lang')
        cb: Gtk.ComboBoxText = self.builder.get_object('cb_lang')
        self._current_lang = cb_store[cb.get_active_iter()][0]
        self._refresh_list()

    def _regenerate_list(self):
        tree_store: Gtk.ListStore = self.builder.get_object('tree_store')

        new_list = []
        for l in tree_store:
            new_list.append((l[2],l[0]))
        new_list.sort()
        new_list = [x[1] for x in new_list]
        self.module.set_i2n(self._current_lang, new_list)
        self._refresh_list()
        
    def on_sort_key_edited(self, widget, path, text):
        try:
            tree_store: Gtk.ListStore = self.builder.get_object('tree_store')
            tree_store[path][0] = int(text)
        except ValueError:
            return
        
        self._regenerate_list()

    def _get_max_key(self):
        tree_store: Gtk.ListStore = self.builder.get_object('tree_store')
        new_list = []
        for l in tree_store:
            new_list.append(l[0])
        return max(new_list)
        
    def _setup_dialog(self):
        dialog: Gtk.Dialog = self.builder.get_object('dialog_add_remove')
        
        self.builder.get_object('id_key_add_remove').set_increments(1,1)
        self.builder.get_object('id_key_add_remove').set_range(0, self._get_max_key())
        self.builder.get_object('id_key_add_remove').set_text(str(0))
        
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        return dialog
        
    def on_btn_fix_clicked(self, *args):
        tree_store: Gtk.ListStore = self.builder.get_object('tree_store')
        new_list = []
        for l in tree_store:
            new_list.append((l[2],l[0]))
        new_list.sort()
        new_list = [x[1] for x in new_list]
        while len(new_list)<1400:
            new_list.append(0)
        self.module.set_i2n(self._current_lang, new_list)
        
        md = SkyTempleMessageDialog(MainController.window(),
                                    Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                    Gtk.ButtonsType.OK,
                                    _("Keys have now been added for all the 1400 items."))
        md.run()
        md.destroy()
        self._refresh_list()
        
        
    def on_btn_insert_clicked(self, *args):
        dialog = self._setup_dialog()
        self.builder.get_object('lbl_add_remove_title').set_text(_("Insert Key Before: "))
        self.builder.get_object('lbl_add_remove_desc').set_text(_("""Insert an item key id before the one selected.
This means all keys with id >= that one will be incremented by 1. """))
        resp = dialog.run()
        dialog.hide()
        if resp == Gtk.ResponseType.OK:
            key = int(self.builder.get_object('id_key_add_remove').get_text())
            tree_store: Gtk.ListStore = self.builder.get_object('tree_store')
            new_list = []
            for l in tree_store:
                if l[0]>=key:
                    new_list.append((l[2],l[0]+1))
                else:
                    new_list.append((l[2],l[0]))
            new_list.sort()
            new_list = [x[1] for x in new_list]
            self.module.set_i2n(self._current_lang, new_list)
            self._refresh_list()
    def on_btn_remove_clicked(self, *args):
        dialog = self._setup_dialog()
        self.builder.get_object('lbl_add_remove_title').set_text(_("Remove Key: "))
        self.builder.get_object('lbl_add_remove_desc').set_text(_("""Remove the item key id selected.
This means all keys with id > that one will be decremented by 1.
A key can't be removed if it's still used by one item. """))
        resp = dialog.run()
        dialog.hide()
        if resp == Gtk.ResponseType.OK:
            key = int(self.builder.get_object('id_key_add_remove').get_text())
            tree_store: Gtk.ListStore = self.builder.get_object('tree_store')
            no_key = []
            for l in tree_store:
                if key==l[0]:
                    no_key.append(l[2])
            if len(no_key)>0:
                display_error(
                    sys.exc_info(),
                    _(f"This key is still used by these items: {', '.join(no_key)}."),
                    _("Error removing key.")
                )
            else:
                new_list = []
                for l in tree_store:
                    if l[0]>key:
                        new_list.append((l[2],l[0]-1))
                    else:
                        new_list.append((l[2],l[0]))
                new_list.sort()
                new_list = [x[1] for x in new_list]
                self.module.set_i2n(self._current_lang, new_list)
                self._refresh_list()
                
    def on_id_key_add_remove_value_changed(self, widget, *args):
        try:
            val = int(widget.get_text())
        except ValueError:
            val = -1

        max_key = self._get_max_key()
        if val<0:
            val = 0
            widget.set_text(str(val))
        elif val>=max_key:
            val=max_key
            widget.set_text(str(val))
    def _refresh_list(self):
        tree_store: Gtk.ListStore = self.builder.get_object('tree_store')
        tree_store.clear()
        lst = []
        for i, x in enumerate(self.module.get_i2n(self._current_lang)):
            lst.append([x, self._string_provider.get_value(StringType.ITEM_NAMES, i), i])
        lst.sort()
        for x in lst:
            tree_store.append(x)
        
