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
import os
from typing import TYPE_CHECKING

from gi.repository import Gtk

from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.module_controller import AbstractController
from skytemple.core.ui_utils import data_dir
from skytemple_files.common.i18n_util import _, f
from skytemple.controller.main import MainController as SkyTempleMainController
from skytemple_files.common.types.file_types import FileType

if TYPE_CHECKING:
    from skytemple.module.script.module import ScriptModule


class MapController(AbstractController):
    def __init__(self, module: 'ScriptModule', name):
        self.module = module
        self.builder = None
        self.name = name
        self._sub_enter = None
        self._sub_acting = None
        self._sub_sub = None

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'map.glade')
        self.builder.connect_signals(self)
        self.builder.get_object('title').set_text(f(_('Script Scenes for "{}"').format(self.name)))
        self.builder.get_object('desc').set_text(
            f(_('This section contains all scenes for the map {self.name}.\n\n'
                '"Enter (sse)" contains the scene that is loaded when the map is entered\n'
                'by the player by "walking into it" (if applicable).\n\n'
                '"Acting (ssa)" contains the scenes used for cutscenes.\n'
                'The player can usually not move the character in these scenes.\n\n'
                '"Sub (sss)" contains scenes that can be loaded on on top of the "Enter" scene,\n'
                'depending on the current story progress.'))
        )
        self._sub_enter, self._sub_acting, self._sub_sub = self.module.get_subnodes(self.name)
        if self._sub_enter:
            self.builder.get_object('btn_add_enter').set_sensitive(False)
        return self.builder.get_object('box_list')

    def on_btn_add_enter_clicked(self, *args):
        try:
            self.module.add_scene_enter(self.name)
        except ValueError as err:
            md = SkyTempleMessageDialog(
                SkyTempleMainController.window(),
                Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR,
                Gtk.ButtonsType.OK,
                _("Could not add the scene: ") + str(err)
            )
            md.run()
            md.destroy()
            return
        md = SkyTempleMessageDialog(
            SkyTempleMainController.window(),
            Gtk.DialogFlags.MODAL, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("Scene added successfully"), is_success=True
        )
        md.run()
        md.destroy()
        self.builder.get_object('btn_add_enter').set_sensitive(False)

    def on_btn_add_acting_clicked(self, *args):
        response, name = self._show_generic_input(_('Scene Name (without file extension)'), _('Create Scene'))
        if response != Gtk.ResponseType.OK:
            return
        name_file = name.lower()
        if len(name) < 1 or len(name) > 8:
            md = SkyTempleMessageDialog(
                SkyTempleMainController.window(),
                Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR,
                Gtk.ButtonsType.OK,
                _("The length of the scene name must be between 1-8 characters.")
            )
            md.run()
            md.destroy()
            return
        try:
            self.module.add_scene_acting(self.name, name_file)
        except ValueError as err:
            md = SkyTempleMessageDialog(
                SkyTempleMainController.window(),
                Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR,
                Gtk.ButtonsType.OK,
                _("Could not add the scene: ") + str(err)
            )
            md.run()
            md.destroy()
            return
        md = SkyTempleMessageDialog(
            SkyTempleMainController.window(),
            Gtk.DialogFlags.MODAL, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("Scene added successfully"), is_success=True
        )
        md.run()
        md.destroy()

    def on_btn_add_sub_clicked(self, *args):
        response, name = self._show_generic_input(_('Scene Name (without file extension)'), _('Create Scene'))
        if response != Gtk.ResponseType.OK:
            return
        name_file = name.lower()
        if len(name) < 1 or len(name) > 8:
            md = SkyTempleMessageDialog(
                SkyTempleMainController.window(),
                Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR,
                Gtk.ButtonsType.OK,
                _("The length of the scene name must be between 1-8 characters.")
            )
            md.run()
            md.destroy()
            return
        try:
            self.module.add_scene_sub(self.name, name_file)
        except ValueError as err:
            md = SkyTempleMessageDialog(
                SkyTempleMainController.window(),
                Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR,
                Gtk.ButtonsType.OK,
                _("Could not add the scene: ") + str(err)
            )
            md.run()
            md.destroy()
            return
        md = SkyTempleMessageDialog(
            SkyTempleMainController.window(),
            Gtk.DialogFlags.MODAL, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("Scene added successfully"), is_success=True
        )
        md.run()
        md.destroy()

    def _show_generic_input(self, label_text, ok_text):
        dialog: Gtk.Dialog = self.builder.get_object('generic_input_dialog')
        entry: Gtk.Entry = self.builder.get_object('generic_input_dialog_entry')
        label: Gtk.Label = self.builder.get_object('generic_input_dialog_label')
        label.set_text(label_text)
        btn_cancel = dialog.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        btn = dialog.add_button(ok_text, Gtk.ResponseType.OK)
        btn.set_can_default(True)
        btn.grab_default()
        entry.set_activates_default(True)
        dialog.set_attached_to(SkyTempleMainController.window())
        dialog.set_transient_for(SkyTempleMainController.window())
        response = dialog.run()
        dialog.hide()
        btn.get_parent().remove(btn)
        btn_cancel.get_parent().remove(btn_cancel)
        return response, entry.get_text()
