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
import os
from typing import TYPE_CHECKING, Optional, cast
from gi.repository import Gtk
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.ui_utils import data_dir, assert_not_none, safe_destroy
from skytemple_files.common.i18n_util import _
from skytemple.controller.main import MainController as SkyTempleMainController
from skytemple.init_locale import LocalePatchedGtkTemplate

if TYPE_CHECKING:
    from skytemple.module.sprite.module import SpriteModule
OBJECT_SPRTIES = _("Object Sprites")


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "sprite", "object_main.ui"))
class StSpriteObjectMainPage(Gtk.Box):
    __gtype_name__ = "StSpriteObjectMainPage"
    module: SpriteModule
    item_data: int
    btn_add: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    generic_input_dialog: Gtk.Dialog = cast(Gtk.Dialog, Gtk.Template.Child())
    generic_input_dialog_label: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    generic_input_dialog_entry: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())

    def __init__(self, module: SpriteModule, item_data: int):
        super().__init__()
        self.module = module
        self.item_data = item_data

    @Gtk.Template.Callback()
    def on_self_destroy(self, *args):
        # Try to destroy all top-level widgets outside of the template to not leak memory.
        safe_destroy(self.generic_input_dialog)

    @Gtk.Template.Callback()
    def on_btn_add_clicked(self, *args):
        from skytemple.module.sprite.module import GROUND_DIR, WAN_FILE_EXT

        response, name = self._show_generic_input(_("Sprite Name"), _("Create Object Sprite"))
        if response != Gtk.ResponseType.OK:
            return
        name = name.lower()
        if len(name) < 1 or len(name) > 10:
            md = SkyTempleMessageDialog(
                SkyTempleMainController.window(),
                Gtk.DialogFlags.MODAL,
                Gtk.MessageType.ERROR,
                Gtk.ButtonsType.OK,
                _("The length of the sprite name must be between 1-10 characters."),
            )
            md.run()
            md.destroy()
            return
        obj_name = f"{GROUND_DIR}/{name}.{WAN_FILE_EXT}"
        if self.module.project.file_exists(obj_name):
            md = SkyTempleMessageDialog(
                SkyTempleMainController.window(),
                Gtk.DialogFlags.MODAL,
                Gtk.MessageType.ERROR,
                Gtk.ButtonsType.OK,
                _("A sprite with this name already exists."),
            )
            md.run()
            md.destroy()
            return
        with open(os.path.join(data_dir(), "empty.wan"), "rb") as f:
            empty_wan = f.read()
        # Write to ROM
        self.module.project.create_file_manually(obj_name, empty_wan)
        self.module.add_wan(f"{name}.{WAN_FILE_EXT}")
        md = SkyTempleMessageDialog(
            SkyTempleMainController.window(),
            Gtk.DialogFlags.MODAL,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("Object sprite added successfully"),
            is_success=True,
        )
        md.run()
        md.destroy()

    def _show_generic_input(self, label_text, ok_text):
        dialog = self.generic_input_dialog
        entry = self.generic_input_dialog_entry
        label = self.generic_input_dialog_label
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
        assert_not_none(cast(Optional[Gtk.Container], btn.get_parent())).remove(btn)
        assert_not_none(cast(Optional[Gtk.Container], btn_cancel.get_parent())).remove(btn_cancel)
        return (response, entry.get_text())
