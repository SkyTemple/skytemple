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
import sys
from typing import TYPE_CHECKING, Optional, List
from skytemple_files.common.i18n_util import _, f

from gi.repository import Gtk

from skytemple.core.error_handler import display_error
from skytemple.controller.main import MainController
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.module_controller import AbstractController
from skytemple.core.string_provider import StringType
if TYPE_CHECKING:
    from skytemple.module.lists.module import ListsModule

logger = logging.getLogger(__name__)


class ItemEffectsController(AbstractController):
    def __init__(self, module: 'ListsModule', *args):
        super().__init__(module, *args)
        self.module = module
        self.item_effects = None
        self._string_provider = module.project.get_string_provider()

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'item_effects.glade')
        stack: Gtk.Stack = self.builder.get_object('list_stack')

        if not self.module.has_item_effects():
            stack.set_visible_child(self.builder.get_object('box_na'))
            return stack
        self.item_effects = self.module.get_item_effects()

        self._init_item_list()
        self._init_combos()
        self.on_cb_effect_ids_changed()
        
        stack.set_visible_child(self.builder.get_object('box_list'))
        self.builder.connect_signals(self)
        
        return stack

    def _get_current_item_effect(self) -> Optional[int]:
        tree_store: Gtk.ListStore = self.builder.get_object('item_effects_store')
        active_rows : List[Gtk.TreePath] = self.builder.get_object('items_tree').get_selection().get_selected_rows()[1]

        item_effect = None
        for x in active_rows:
            item_effect = tree_store[x.get_indices()[0]][2]
        return item_effect
    
    def _get_current_effect(self) -> int:
        cb_store: Gtk.ListStore = self.builder.get_object('effect_ids_store')
        cb: Gtk.ComboBoxText = self.builder.get_object('cb_effect_ids')

        if cb.get_active_iter()!=None:
            return cb_store[cb.get_active_iter()][0]
        else:
            return 0

    def _init_item_list(self):
        # Init available menus
        item_store: Gtk.ListStore = self.builder.get_object('item_effects_store')
        # Init list
        item_store.clear()

        non_sorted = []
        for i in range(self.item_effects.nb_items()):
            non_sorted.append([i,
                               self._string_provider.get_value(StringType.ITEM_NAMES, i),
                               self.item_effects.get_item_effect_id(i)])
        for x in sorted(non_sorted, key=lambda x:x[1]):
            item_store.append(x)
        
    def _init_combos(self, active=0):
        # Init available menus
        cb_store: Gtk.ListStore = self.builder.get_object('effect_ids_store')
        cb: Gtk.ComboBoxText = self.builder.get_object('cb_effect_ids')
        # Init combobox
        cb_store.clear()
        for i in range(self.item_effects.nb_effects()):
            cb_store.append([i, f'Effect {i}'])
        cb.set_active(active)

    def on_btn_import_code_clicked(self, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("Import any item effect ASM code. It must follow the rules of a valid item effect code.\n"
              "WARNING: SkyTemple does not check if the code is correct!\n"
              "Also, make sure the code was assembled for the version you are using. "),
            title=_("Import Item Effect ASM Code")
        )
        md.run()
        md.destroy()
        dialog = Gtk.FileChooserNative.new(
            _("Import Item Effect ASM Code..."),
            MainController.window(),
            Gtk.FileChooserAction.OPEN,
            None, None
        )

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            try:
                with open(fn, 'rb') as file:
                    self.item_effects.set_effect_code(self._get_current_effect(), file.read())
                self.module.mark_item_effects_as_modified()
            except Exception as err:
                display_error(
                    sys.exc_info(),
                    str(err),
                    _("Error importing ASM code.")
                )
    
    def on_btn_export_code_clicked(self, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("Export any item effect ASM code. It must follow the rules of a valid item effect code.\n"
              "WARNING: it only exports the raw code, it doesn't disassemble it!"),
            title=_("Export Item Effect ASM Code")
        )
        md.run()
        md.destroy()
        dialog = Gtk.FileChooserNative.new(
            _("Export Item Effect ASM Code..."),
            MainController.window(),
            Gtk.FileChooserAction.SAVE,
            None, None
        )

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            with open(fn, 'wb') as file:
                file.write(self.item_effects.get_effect_code(self._get_current_effect()))
        
    def on_btn_add_effect_clicked(self, *args):
        self.item_effects.add_effect_code(bytes([0x64, 0x09, 0x00, 0xEA])) # Branch to the end
        self._init_combos(self.item_effects.nb_effects()-1)
        self.module.mark_item_effects_as_modified()
        
    def on_btn_remove_effect_clicked(self, *args):
        try:
            effect_id = self._get_current_effect()
            self.item_effects.del_effect_code(effect_id)
            self._init_combos(min(effect_id, self.item_effects.nb_effects()-1))
            self._init_item_list()
            self.module.mark_item_effects_as_modified()
        except ValueError as err:
            display_error(
                sys.exc_info(),
                str(err),
                "Cannot delete this effect."
            )
        
    def on_btn_goto_effect_clicked(self, *args):
        item_effect = self._get_current_item_effect()
        if item_effect != None:
            cb: Gtk.ComboBoxText = self.builder.get_object('cb_effect_ids')
            cb.set_active(item_effect)
            effects_notebook = self.builder.get_object('effects_notebook')
            effects_notebook.set_current_page(1)
        
    def on_item_effect_id_edited(self, widget, path, text):
        try:
            if int(text)>=self.item_effects.nb_effects() or int(text)<0:
                return
            tree_store: Gtk.ListStore = self.builder.get_object('item_effects_store')
            tree_store[path][2] = int(text)
        except ValueError:
            return
        self.item_effects.set_item_effect_id(tree_store[path][0], tree_store[path][2])
        self.on_cb_effect_ids_changed()
        self.module.mark_item_effects_as_modified()
        
    def on_cb_effect_ids_changed(self, *args):
        effect_id = self._get_current_effect()
        store = self.builder.get_object('effect_items_store')
        store.clear()
        for x in self.item_effects.get_all_of(effect_id):
            store.append([x, self._string_provider.get_value(StringType.ITEM_NAMES, x)])
