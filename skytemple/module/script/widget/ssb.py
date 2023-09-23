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
from __future__ import annotations
import os
from typing import TYPE_CHECKING

from gi.repository import Gtk

from skytemple.controller.main import MainController
from skytemple.core.ui_utils import data_dir

if TYPE_CHECKING:
    from skytemple.module.script.module import ScriptModule


@Gtk.Template(filename=os.path.join(data_dir(), "widget", "script", "ssb_page.ui"))
class StScriptSsbPage(Gtk.Box):
    __gtype_name__ = "StScriptSsbPage"

    module: ScriptModule
    item_data: None

    # noinspection PyUnusedLocal
    def __init__(self, module: ScriptModule, item_data):
        super().__init__()

        self.module = module
        self.item_data = item_data

    @Gtk.Template.Callback()
    def on_button_script_debugger_clicked(self, *args):
        MainController.debugger_manager().open(MainController.window())
