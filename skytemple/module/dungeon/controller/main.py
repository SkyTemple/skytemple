#  Copyright 2020 Parakoopa
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
from typing import TYPE_CHECKING

from gi.repository import Gtk

from skytemple.core.module_controller import AbstractController
if TYPE_CHECKING:
    from skytemple.module.dungeon.module import DungeonModule

DUNGEONS_NAME = 'Dungeons'


class MainController(AbstractController):
    def __init__(self, module: 'DungeonModule', *args):
        self.module = module

        self.builder = None

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'main.glade')
        return self.builder.get_object('main_box')

    def on_edit_groups_clicked(self, *args):
        pass  # todo
