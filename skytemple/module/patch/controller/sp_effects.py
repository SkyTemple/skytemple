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
import sys
import webbrowser
from typing import TYPE_CHECKING, Optional, List

from range_typed_integers import u16_checked, u16

from skytemple.core.ui_utils import REPO_MOVE_EFFECTS, catch_overflow
from skytemple_files.common.i18n_util import _, f

from gi.repository import Gtk

from skytemple.core.error_handler import display_error
from skytemple.controller.main import MainController
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.module_controller import AbstractController
from skytemple.core.string_provider import StringType
from skytemple_files.common.util import open_utf8
from skytemple_files.data.data_cd.model import DataCD

if TYPE_CHECKING:
    from skytemple.module.patch.module import PatchModule
from skytemple_files.common.i18n_util import _

logger = logging.getLogger(__name__)


class SPEffectsController(AbstractController):
    def __init__(self, module: 'PatchModule', *args):
        super().__init__(module, *args)
        self.module = module
        self.builder: Gtk.Builder
        self.sp_effects: DataCD
        self._string_provider = module.project.get_string_provider()

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'sp_effects.glade')
        stack: Gtk.Stack = self.builder.get_object('list_stack')

        if not self.module.has_sp_effects():
            stack.set_visible_child(self.builder.get_object('box_na'))
            return stack
        self.sp_effects = self.module.get_sp_effects()

        self._init_sp_list()
        self._init_combos()
        self.on_cb_effect_ids_changed()
        
        stack.set_visible_child(self.builder.get_object('box_list'))
        self.builder.connect_signals(self)
        
        return stack

    def _get_current_sp_effect(self) -> Optional[int]:
        tree_store: Gtk.ListStore = self.builder.get_object('sp_effects_store')
        active_rows : List[Gtk.TreePath] = self.builder.get_object('sps_tree').get_selection().get_selected_rows()[1]

        sp_effect = None
        for x in active_rows:
            sp_effect = tree_store[x.get_indices()[0]][1]
        return sp_effect
    
    def _get_current_effect(self) -> int:
        cb_store: Gtk.ListStore = self.builder.get_object('effect_ids_store')
        cb: Gtk.ComboBoxText = self.builder.get_object('cb_effect_ids')

        if cb.get_active_iter()!=None:
            return cb_store[cb.get_active_iter()][0]
        else:
            return 0

    def _init_sp_list(self):
        # Init available menus
        sp_store: Gtk.ListStore = self.builder.get_object('sp_effects_store')
        # Init list
        sp_store.clear()
        for i in range(self.sp_effects.nb_items()):
            sp_store.append([i, self.sp_effects.get_item_effect_id(i)])
        
    def _init_combos(self, active=0):
        # Init available menus
        cb_store: Gtk.ListStore = self.builder.get_object('effect_ids_store')
        cb: Gtk.ComboBoxText = self.builder.get_object('cb_effect_ids')
        # Init combobox
        cb_store.clear()
        for i in range(self.sp_effects.nb_effects()):
            cb_store.append([i, f'Effect {i}'])
        cb.set_active(active)

    def on_btn_import_code_clicked(self, *args):
        dialog = Gtk.FileChooserNative.new(
            _("Import Special Process Effect ASM Code..."),
            MainController.window(),
            Gtk.FileChooserAction.OPEN,
            None, None
        )

        filter = Gtk.FileFilter()
        filter.set_name(_("Any Files"))
        filter.add_pattern("*")
        dialog.add_filter(filter)

        filter = Gtk.FileFilter()
        filter.set_name(_("armips ASM patches (*.asm)"))
        filter.add_pattern("*.asm")
        dialog.add_filter(filter)

        filter = Gtk.FileFilter()
        filter.set_name(_("Raw code (*.bin)"))
        filter.add_pattern("*.bin")
        dialog.add_filter(filter)

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            try:
                if fn.split('.')[-1].lower() == 'asm':
                    with open_utf8(fn, 'r') as file:
                        self.sp_effects.import_armips_effect_code(self._get_current_effect(), file.read())
                else:
                    with open(fn, 'rb') as file:
                        self.sp_effects.set_effect_code(self._get_current_effect(), file.read())
                self.module.mark_sp_effects_as_modified()
            except Exception as err:
                display_error(
                    sys.exc_info(),
                    str(err),
                    _("Error importing ASM code.")
                )

    def on_tv_paste_import_buffer_paste_done(self, buff: Gtk.TextBuffer, *args):
        text = buff.get_text(buff.get_start_iter(), buff.get_end_iter(), False)
        buff.delete(buff.get_start_iter(), buff.get_end_iter())
        try:
            self.sp_effects.import_armips_effect_code(self._get_current_effect(), text)  # type: ignore
            self.module.mark_sp_effects_as_modified()
            md = SkyTempleMessageDialog(
                MainController.window(),
                Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                Gtk.ButtonsType.OK,
                _("Patch successfully imported."),
                is_success=True
            )
            md.run()
            md.destroy()
        except Exception as err:
            display_error(
                sys.exc_info(),
                str(err),
                _("Error importing ASM code.")
            )

    def on_btn_export_code_clicked(self, *args):
        dialog = Gtk.FileChooserNative.new(
            _("Export Special Process Effect ASM Code..."),
            MainController.window(),
            Gtk.FileChooserAction.SAVE,
            None, None
        )

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            with open(fn, 'wb') as file:
                file.write(self.sp_effects.get_effect_code(self._get_current_effect()))

    def on_btn_help_import_clicked(self):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("""Export and import effect code.
The export only exports the raw machine code. It is NOT disassembled.
The import accepts both armips ASM code or the raw binary machine code.
Please note, that SkyTemple does not check the raw code you try to import.
If you import armips ASM code, an effect code library is available.

You can use the ASM Editor tool to generate patch files.
The ASM patch must generate a 'code_out.bin' file, which SkyTemple will try to import.
"""),
            title=_("Export / Import Effect Code Help")
        )
        md.run()
        md.destroy()

    def on_btn_repo_clicked(self, *args):
        webbrowser.open_new_tab(REPO_MOVE_EFFECTS)

    def on_btn_asmeditor_clicked(self, *args):
        webbrowser.open_new_tab('https://asmeditor.skytemple.org/')

    def on_btn_add_effect_clicked(self, *args):
        self.sp_effects.add_effect_code(bytes([0x1C, 0x2, 0x00, 0xEA])) # Branch to the end
        self._init_combos(self.sp_effects.nb_effects()-1)
        self.module.mark_sp_effects_as_modified()
        
    def on_btn_remove_effect_clicked(self, *args):
        try:
            effect_id = self._get_current_effect()
            self.sp_effects.del_effect_code(effect_id)
            self._init_combos(min(effect_id, self.sp_effects.nb_effects()-1))
            self._init_sp_list()
            self.module.mark_sp_effects_as_modified()
        except ValueError as err:
            display_error(
                sys.exc_info(),
                str(err),
                "Cannot delete this effect."
            )
        
    def on_btn_goto_effect_clicked(self, *args):
        sp_effect = self._get_current_sp_effect()
        if sp_effect is not None:
            cb: Gtk.ComboBoxText = self.builder.get_object('cb_effect_ids')
            cb.set_active(sp_effect)
            effects_notebook = self.builder.get_object('effects_notebook')
            effects_notebook.set_current_page(1)

    @catch_overflow(u16)
    def on_sp_effect_id_edited(self, widget, path, text):
        try:
            if int(text) >= self.sp_effects.nb_effects() or int(text)<0:
                return
            tree_store: Gtk.ListStore = self.builder.get_object('sp_effects_store')
            tree_store[path][1] = u16_checked(int(text))
        except ValueError:
            return
        self.sp_effects.set_item_effect_id(tree_store[path][0], tree_store[path][1])
        self.on_cb_effect_ids_changed()
        self.module.mark_sp_effects_as_modified()
        
    def on_cb_effect_ids_changed(self, *args):
        effect_id = self._get_current_effect()
        store = self.builder.get_object('effect_sps_store')
        store.clear()
        for x in self.sp_effects.get_all_of(effect_id):
            store.append([x])

    def on_btn_add_sp_clicked(self, *args):
        self.sp_effects.add_item_effect_id(u16(0))
        self._init_sp_list()
        self.module.mark_sp_effects_as_modified()
