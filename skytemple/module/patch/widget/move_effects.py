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
import sys
import webbrowser
from typing import TYPE_CHECKING, cast
from gi.repository import Gtk
from range_typed_integers import u16, u16_checked
from skytemple.core.error_handler import display_error
from skytemple.controller.main import MainController
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.string_provider import StringType
from skytemple.core.ui_utils import (
    REPO_MOVE_EFFECTS,
    catch_overflow,
    assert_not_none,
    data_dir,
)
from skytemple_files.common.util import open_utf8
from skytemple_files.data.data_cd.model import DataCD
from skytemple_files.data.val_list.model import ValList

from skytemple.init_locale import LocalePatchedGtkTemplate

if TYPE_CHECKING:
    from skytemple.module.patch.module import PatchModule
from skytemple_files.common.i18n_util import _

logger = logging.getLogger(__name__)
import os


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "patch", "move_effects.ui"))
class StPatchMoveEffectsPage(Gtk.Stack):
    __gtype_name__ = "StPatchMoveEffectsPage"
    module: PatchModule
    item_data: None
    effect_ids_store: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    effect_moves_store: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    metronome_store: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    move_effects_store: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    tv_paste_import_buffer: Gtk.TextBuffer = cast(Gtk.TextBuffer, Gtk.Template.Child())
    box_na: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    box_list: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    effects_notebook: Gtk.Notebook = cast(Gtk.Notebook, Gtk.Template.Child())
    moves_tree: Gtk.TreeView = cast(Gtk.TreeView, Gtk.Template.Child())
    move_effect_id: Gtk.CellRendererText = cast(Gtk.CellRendererText, Gtk.Template.Child())
    btn_goto_effect: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    btn_fix_nb_items: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    cb_effect_ids: Gtk.ComboBox = cast(Gtk.ComboBox, Gtk.Template.Child())
    btn_add_effect: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    btn_remove_effect: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    effect_tree: Gtk.TreeView = cast(Gtk.TreeView, Gtk.Template.Child())
    btn_import_code: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    tv_paste_import: Gtk.TextView = cast(Gtk.TextView, Gtk.Template.Child())
    btn_export_code: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    btn_help_import: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    btn_repo: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    btn_asmeditor: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    metronome_tree: Gtk.TreeView = cast(Gtk.TreeView, Gtk.Template.Child())
    metronome_move_id: Gtk.CellRendererText = cast(Gtk.CellRendererText, Gtk.Template.Child())
    btn_add_metronome: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    btn_remove_metronome: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())

    def __init__(self, module: PatchModule, item_data: None):
        super().__init__()
        self.module = module
        self.item_data = item_data
        self.move_effects: DataCD
        self.metronome: ValList
        self._string_provider = module.project.get_string_provider()
        if not self.module.has_move_effects() or not self.module.has_metronome_pool():
            self.set_visible_child(self.box_na)
        else:
            self.move_effects = self.module.get_move_effects()
            self.metronome = self.module.get_metronome_pool()
            self._metronome_pool = self.metronome.get_list(4)
            self._init_move_list()
            self._init_combos()
            self.on_cb_effect_ids_changed()
            self.set_visible_child(self.box_list)

    def _get_current_move_effect(self) -> int | None:
        tree_store = self.move_effects_store
        active_rows: list[Gtk.TreePath] = self.moves_tree.get_selection().get_selected_rows()[1]
        move_effect = None
        for x in active_rows:
            move_effect = tree_store[x.get_indices()[0]][2]
        return move_effect

    def _get_current_effect(self) -> int:
        cb_store = self.effect_ids_store
        cb = self.cb_effect_ids
        if cb.get_active_iter() is not None:
            return cb_store[assert_not_none(cb.get_active_iter())][0]
        else:
            return 0

    def _init_move_list(self):
        # Init available moves
        move_store: Gtk.ListStore = self.move_effects_store
        # Init list
        move_store.clear()
        non_sorted = []
        for i in range(self.move_effects.nb_items()):
            non_sorted.append(
                [
                    i,
                    self._string_provider.get_value(StringType.MOVE_NAMES, i),
                    self.move_effects.get_item_effect_id(i),
                ]
            )
        for x in sorted(non_sorted, key=lambda x: x[1]):  # type: ignore
            move_store.append(x)
        # Init available metronome moves
        metronome_store = self.metronome_store
        # Init list
        metronome_store.clear()
        for i in self._metronome_pool:
            metronome_store.append([i, self._string_provider.get_value(StringType.MOVE_NAMES, i)])

    def _init_combos(self, active=0):
        # Init available effects
        cb_store = self.effect_ids_store
        cb = self.cb_effect_ids
        # Init combobox
        cb_store.clear()
        for i in range(self.move_effects.nb_effects()):
            cb_store.append([i, f"Effect {i}"])
        cb.set_active(active)

    @Gtk.Template.Callback()
    def on_btn_import_code_clicked(self, *args):
        dialog = Gtk.FileChooserNative.new(
            _("Import Move Effect ASM Code..."),
            MainController.window(),
            Gtk.FileChooserAction.OPEN,
            None,
            None,
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
        if response == Gtk.ResponseType.ACCEPT and fn is not None:
            try:
                if fn.split(".")[-1].lower() == "asm":
                    with open_utf8(fn, "r") as file:
                        self.move_effects.import_armips_effect_code(self._get_current_effect(), file.read())
                else:
                    with open(fn, "rb") as file:
                        self.move_effects.set_effect_code(self._get_current_effect(), file.read())
                self.module.mark_move_effects_as_modified()
                md = SkyTempleMessageDialog(
                    MainController.window(),
                    Gtk.DialogFlags.DESTROY_WITH_PARENT,
                    Gtk.MessageType.INFO,
                    Gtk.ButtonsType.OK,
                    _("ASM code imported successfully."),
                    is_success=True,
                )
                md.run()
                md.destroy()
            except Exception as err:
                display_error(sys.exc_info(), str(err), _("Error importing ASM code."))

    @Gtk.Template.Callback()
    def on_tv_paste_import_buffer_paste_done(self, buff: Gtk.TextBuffer, *args):
        text = buff.get_text(buff.get_start_iter(), buff.get_end_iter(), False)
        buff.delete(buff.get_start_iter(), buff.get_end_iter())
        try:
            self.move_effects.import_armips_effect_code(self._get_current_effect(), text)
            self.module.mark_move_effects_as_modified()
            md = SkyTempleMessageDialog(
                MainController.window(),
                Gtk.DialogFlags.DESTROY_WITH_PARENT,
                Gtk.MessageType.INFO,
                Gtk.ButtonsType.OK,
                _("ASM code imported successfully."),
                is_success=True,
            )
            md.run()
            md.destroy()
        except Exception as err:
            display_error(sys.exc_info(), str(err), _("Error importing ASM code."))

    @Gtk.Template.Callback()
    def on_btn_export_code_clicked(self, *args):
        dialog = Gtk.FileChooserNative.new(
            _("Export Move Effect ASM Code..."),
            MainController.window(),
            Gtk.FileChooserAction.SAVE,
            None,
            None,
        )
        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()
        if response == Gtk.ResponseType.ACCEPT and fn is not None:
            with open(fn, "wb") as file:
                file.write(self.move_effects.get_effect_code(self._get_current_effect()))

    @Gtk.Template.Callback()
    def on_btn_help_import_clicked(self, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _(
                "Export and import effect code.\nThe export only exports the raw machine code. It is NOT disassembled.\nThe import accepts both armips ASM code or the raw binary machine code.\nPlease note, that SkyTemple does not check the raw code you try to import.\nIf you import armips ASM code, an effect code library is available.\n\nYou can use the ASM Editor tool to generate patch files.\nThe ASM patch must generate a 'code_out.bin' file, which SkyTemple will try to import.\n"
            ),
            title=_("Export / Import Effect Code Help"),
        )
        md.run()
        md.destroy()

    @Gtk.Template.Callback()
    def on_btn_repo_clicked(self, *args):
        webbrowser.open_new_tab(REPO_MOVE_EFFECTS)

    @Gtk.Template.Callback()
    def on_btn_asmeditor_clicked(self, *args):
        webbrowser.open_new_tab("https://asmeditor.skytemple.org/")

    @Gtk.Template.Callback()
    def on_btn_add_effect_clicked(self, *args):
        self.move_effects.add_effect_code(bytes([100, 9, 0, 234]))  # Branch to the end
        self._init_combos(self.move_effects.nb_effects() - 1)
        self.module.mark_move_effects_as_modified()

    @Gtk.Template.Callback()
    def on_btn_remove_effect_clicked(self, *args):
        try:
            effect_id = self._get_current_effect()
            self.move_effects.del_effect_code(effect_id)
            self._init_combos(min(effect_id, self.move_effects.nb_effects() - 1))
            self._init_move_list()
            self.module.mark_move_effects_as_modified()
        except ValueError as err:
            display_error(sys.exc_info(), str(err), _("Cannot delete this effect."))

    @Gtk.Template.Callback()
    def on_metronome_move_id_edited(self, widget, path, text):
        try:
            tree_store = self.metronome_store
            new = int(text)
            tree_store[path][0] = new
            tree_store[path][1] = self._string_provider.get_value(StringType.MOVE_NAMES, new)
        except ValueError:
            return
        self._metronome_pool[int(path)] = new
        self._push_metronome_pool()

    def _push_metronome_pool(self):
        self.metronome.set_list(self._metronome_pool, 4)
        self.module.mark_metronome_pool_as_modified()

    @Gtk.Template.Callback()
    def on_btn_add_metronome_clicked(self, *args):
        metronome_store = self.metronome_store
        metronome_store.append([0, self._string_provider.get_value(StringType.MOVE_NAMES, 0)])
        self._metronome_pool.append(0)
        self._push_metronome_pool()

    @Gtk.Template.Callback()
    def on_btn_remove_metronome_clicked(self, *args):
        # Deletes all selected metronome entries
        # Allows multiple deletions
        active_rows: list[Gtk.TreePath] = self.metronome_tree.get_selection().get_selected_rows()[1]
        metronome_store = self.metronome_store
        for x in reversed(sorted(active_rows, key=lambda x: x.get_indices())):
            index = x.get_indices()[0]
            del self._metronome_pool[index]
            del metronome_store[index]
        self._push_metronome_pool()

    @Gtk.Template.Callback()
    def on_btn_goto_effect_clicked(self, *args):
        move_effect = self._get_current_move_effect()
        if move_effect is not None:
            cb = self.cb_effect_ids
            cb.set_active(move_effect)
            effects_notebook = self.effects_notebook
            effects_notebook.set_current_page(1)

    @Gtk.Template.Callback()
    def on_btn_fix_nb_items_clicked(self, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _(
                "This will change the number of moves to 559, in case there isn't enough moves in the list.\nused to fix the previous amount of move effects extracted by the previous versions of the patch."
            ),
            title=_("Fix Number of Moves"),
        )
        md.run()
        md.destroy()
        while self.move_effects.nb_items() < 559:
            self.move_effects.add_item_effect_id(u16(0))
        self.module.mark_move_effects_as_modified()
        self._init_move_list()

    @Gtk.Template.Callback()
    @catch_overflow(u16)
    def on_move_effect_id_edited(self, widget, path, text):
        try:
            if int(text) >= self.move_effects.nb_effects() or int(text) < 0:
                return
            tree_store = self.move_effects_store
            tree_store[path][2] = u16_checked(int(text))
        except ValueError:
            return
        self.move_effects.set_item_effect_id(tree_store[path][0], tree_store[path][2])
        self.on_cb_effect_ids_changed()
        self.module.mark_move_effects_as_modified()

    @Gtk.Template.Callback()
    def on_cb_effect_ids_changed(self, *args):
        effect_id = self._get_current_effect()
        store = self.effect_moves_store
        store.clear()
        for x in self.move_effects.get_all_of(effect_id):
            store.append([x, self._string_provider.get_value(StringType.MOVE_NAMES, x)])
