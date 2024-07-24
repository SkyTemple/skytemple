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
from typing import TYPE_CHECKING, cast
from gi.repository import Gtk
from skytemple.core.open_request import OpenRequest, REQUEST_TYPE_DUNGEONS
from skytemple.core.string_provider import StringType
from skytemple.core.ui_utils import data_dir
from skytemple.init_locale import LocalePatchedGtkTemplate

if TYPE_CHECKING:
    from skytemple.module.dungeon.module import DungeonModule, DungeonViewInfo
import os


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "dungeon", "invalid.ui"))
class StDungeonInvalidDungeonPage(Gtk.Box):
    __gtype_name__ = "StDungeonInvalidDungeonPage"
    module: DungeonModule
    item_data: DungeonViewInfo
    cb_direction_store: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    label_dungeon_name: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    btn_goto: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    spin_floor_count_adjument: Gtk.Adjustment = cast(Gtk.Adjustment, Gtk.Template.Child())

    def __init__(self, module: DungeonModule, item_data: DungeonViewInfo):
        super().__init__()
        self.module = module
        self.item_data = item_data
        self.dungeon_name = self.module.project.get_string_provider().get_value(
            StringType.DUNGEON_NAMES_MAIN, self.item_data.dungeon_id
        )
        self.label_dungeon_name.set_text(self.dungeon_name)

    @Gtk.Template.Callback()
    def on_btn_goto_clicked(self, *args):
        self.module.project.request_open(OpenRequest(REQUEST_TYPE_DUNGEONS, None))
