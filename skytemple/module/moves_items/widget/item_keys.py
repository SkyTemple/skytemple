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
import sys
from typing import TYPE_CHECKING, cast
from gi.repository import Gtk
from skytemple.core.error_handler import display_error
from skytemple.controller.main import MainController
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.string_provider import StringType
from skytemple.core.ui_utils import (
    iter_tree_model,
    assert_not_none,
    data_dir,
    safe_destroy,
)
from skytemple_files.common.i18n_util import _

from skytemple.init_locale import LocalePatchedGtkTemplate

if TYPE_CHECKING:
    from skytemple.module.moves_items.module import MovesItemsModule
PATTERN_ITEM_ENTRY = re.compile(".*\\(#(\\d+)\\).*")
logger = logging.getLogger(__name__)
import os


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "moves_items", "item_keys.ui"))
class StMovesItemsItemKeysPage(Gtk.Box):
    __gtype_name__ = "StMovesItemsItemKeysPage"
    module: MovesItemsModule
    item_data: None
    cb_store_lang: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    dialog_add_remove: Gtk.Dialog = cast(Gtk.Dialog, Gtk.Template.Child())
    btn_ok: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    btn_cancel: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    lbl_add_remove_title: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    id_key_add_remove: Gtk.SpinButton = cast(Gtk.SpinButton, Gtk.Template.Child())
    lbl_add_remove_desc: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    tree_store: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    cb_lang: Gtk.ComboBox = cast(Gtk.ComboBox, Gtk.Template.Child())
    tree: Gtk.TreeView = cast(Gtk.TreeView, Gtk.Template.Child())
    sort_key: Gtk.CellRendererText = cast(Gtk.CellRendererText, Gtk.Template.Child())
    item_name: Gtk.CellRendererText = cast(Gtk.CellRendererText, Gtk.Template.Child())
    btn_insert: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    btn_remove: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    btn_fix: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    btn_help: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())

    def __init__(self, module: MovesItemsModule, item_data: None):
        super().__init__()
        self.module = module
        self.item_data = item_data
        self._string_provider = module.project.get_string_provider()
        self._init_combos()
        self.on_lang_changed()

    @Gtk.Template.Callback()
    def on_self_destroy(self, *args):
        # Try to destroy all top-level widgets outside of the template to not leak memory.
        safe_destroy(self.dialog_add_remove)

    def _init_combos(self):
        # Init available languages
        cb_store = self.cb_store_lang
        cb = self.cb_lang
        # Init combobox
        cb_store.clear()
        for lang in self._string_provider.get_languages():
            cb_store.append([lang.locale, lang.name_localized])
        cb.set_active(0)

    @Gtk.Template.Callback()
    def on_btn_help_clicked(self, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _(
                "Sort keys are used to sort items in your inventory when using the sort feature in game.\nThe game sorts items starting from the one with the lowest key to the highest.\nSeveral items can have the same key; this means they will be mixed together while sorting (e.g. Lookalike items).\nOnly keys from 0 to 2047 should be used."
            ),
        )
        md.run()
        md.destroy()

    @Gtk.Template.Callback()
    def on_lang_changed(self, *args):
        cb_store = self.cb_store_lang
        cb = self.cb_lang
        self._current_lang = cb_store[assert_not_none(cb.get_active_iter())][0]
        self._refresh_list()

    def _regenerate_list(self):
        tree_store = self.tree_store
        pre_new_list = []
        for lst in iter_tree_model(tree_store):
            pre_new_list.append((lst[2], lst[0]))
        pre_new_list.sort()
        new_list = [x[1] for x in pre_new_list]
        self.module.set_i2n(self._current_lang, new_list)
        self._refresh_list()

    @Gtk.Template.Callback()
    def on_sort_key_edited(self, widget, path, text):
        try:
            tree_store = self.tree_store
            tree_store[path][0] = int(text)
        except ValueError:
            return
        self._regenerate_list()

    def _get_max_key(self):
        tree_store = self.tree_store
        new_list = []
        for lst in iter_tree_model(tree_store):
            new_list.append(lst[0])
        return max(new_list)

    def _setup_dialog(self):
        dialog = self.dialog_add_remove
        self.id_key_add_remove.set_increments(1, 1)
        self.id_key_add_remove.set_range(0, self._get_max_key())
        self.id_key_add_remove.set_text(str(0))
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())
        return dialog

    @Gtk.Template.Callback()
    def on_btn_fix_clicked(self, *args):
        tree_store = self.tree_store
        pre_new_list = []
        for lst in iter_tree_model(tree_store):
            pre_new_list.append((lst[2], lst[0]))
        pre_new_list.sort()
        new_list = [x[1] for x in pre_new_list]
        while len(new_list) < 1400:
            new_list.append(0)
        self.module.set_i2n(self._current_lang, new_list)
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("Keys have now been added for all the 1400 items."),
        )
        md.run()
        md.destroy()
        self._refresh_list()

    @Gtk.Template.Callback()
    def on_btn_insert_clicked(self, *args):
        dialog = self._setup_dialog()
        self.lbl_add_remove_title.set_text(_("Insert Key Before: "))
        self.lbl_add_remove_desc.set_text(
            _(
                "Insert an item key id before the one selected.\nThis means all keys with id >= that one will be incremented by 1. "
            )
        )
        resp = dialog.run()
        dialog.hide()
        if resp == Gtk.ResponseType.OK:
            key = int(self.id_key_add_remove.get_text())
            tree_store = self.tree_store
            pre_new_list = []
            for lst in iter_tree_model(tree_store):
                if lst[0] >= key:
                    pre_new_list.append((lst[2], lst[0] + 1))
                else:
                    pre_new_list.append((lst[2], lst[0]))
            pre_new_list.sort()
            new_list = [x[1] for x in pre_new_list]
            self.module.set_i2n(self._current_lang, new_list)
            self._refresh_list()

    @Gtk.Template.Callback()
    def on_btn_remove_clicked(self, *args):
        dialog = self._setup_dialog()
        self.lbl_add_remove_title.set_text(_("Remove Key: "))
        self.lbl_add_remove_desc.set_text(
            _(
                "Remove the item key id selected.\nThis means all keys with id > that one will be decremented by 1.\nA key can't be removed if it's still used by one item. "
            )
        )
        resp = dialog.run()
        dialog.hide()
        if resp == Gtk.ResponseType.OK:
            key = int(self.id_key_add_remove.get_text())
            tree_store = self.tree_store
            no_key = []
            for lst in iter_tree_model(tree_store):
                if key == lst[0]:
                    no_key.append(str(lst[2]))
            if len(no_key) > 0:
                display_error(
                    sys.exc_info(),
                    _(f"This key is still used by these items: {', '.join(no_key)}."),
                    _("Error removing key."),
                )
            else:
                pre_new_list = []
                for lst in iter_tree_model(tree_store):
                    if lst[0] > key:
                        pre_new_list.append((lst[2], lst[0] - 1))
                    else:
                        pre_new_list.append((lst[2], lst[0]))
                pre_new_list.sort()
                new_list = [x[1] for x in pre_new_list]
                self.module.set_i2n(self._current_lang, new_list)
                self._refresh_list()

    @Gtk.Template.Callback()
    def on_id_key_add_remove_value_changed(self, widget, *args):
        try:
            val = int(widget.get_text())
        except ValueError:
            val = -1
        max_key = self._get_max_key()
        if val < 0:
            val = 0
            widget.set_text(str(val))
        elif val >= max_key:
            val = max_key
            widget.set_text(str(val))

    def _refresh_list(self):
        tree_store = self.tree_store
        tree_store.clear()
        lst = []
        for i, x in enumerate(self.module.get_i2n(self._current_lang)):
            lst.append([x, self._string_provider.get_value(StringType.ITEM_NAMES, i), i])
        lst.sort()
        for y in lst:
            tree_store.append(y)
