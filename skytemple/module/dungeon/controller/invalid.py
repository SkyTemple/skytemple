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
from typing import TYPE_CHECKING, Optional

from gi.repository import Gtk
from gi.repository.Gtk import ResponseType

from skytemple.controller.main import MainController
from skytemple.core.module_controller import AbstractController
from skytemple.core.open_request import OpenRequest, REQUEST_TYPE_DUNGEONS
from skytemple.core.string_provider import StringType
from skytemple_files.hardcoded.dungeons import DungeonRestrictionDirection

from skytemple.core.ui_utils import builder_get_assert

if TYPE_CHECKING:
    from skytemple.module.dungeon.module import DungeonModule, DungeonViewInfo


class InvalidDungeonController(AbstractController):
    def __init__(self, module: 'DungeonModule', dungeon_info: 'DungeonViewInfo'):
        self.module = module
        self.dungeon_info = dungeon_info
        self.dungeon_name = self.module.project.get_string_provider().get_value(
            StringType.DUNGEON_NAMES_MAIN, self.dungeon_info.dungeon_id
        )

        self.builder: Gtk.Builder = None  # type: ignore

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'invalid.glade')
        assert self.builder

        builder_get_assert(self.builder, Gtk.Label, 'label_dungeon_name').set_text(self.dungeon_name)
        self.builder.connect_signals(self)

        return builder_get_assert(self.builder, Gtk.Widget, 'main_box')

    def on_btn_goto_clicked(self, *args):
        self.module.project.request_open(OpenRequest(
            REQUEST_TYPE_DUNGEONS, None
        ))
