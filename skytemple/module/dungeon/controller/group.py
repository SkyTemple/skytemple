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
from typing import TYPE_CHECKING

from gi.repository import Gtk

from skytemple.core.module_controller import SimpleController
from skytemple_files.common.i18n_util import _
if TYPE_CHECKING:
    from skytemple.module.dungeon.module import DungeonModule


class GroupController(SimpleController):
    def __init__(self, module: 'DungeonModule', base_dungeon_id: int):
        self.module = module
        self.base_dungeon_id = base_dungeon_id

    def get_title(self) -> str:
        return self.module.generate_group_label(self.base_dungeon_id)

    def get_content(self) -> Gtk.Widget:
        return self.generate_content_label(
            _('Dungeon groups contain multiple dungeon to create one big continuous dungeon.\n'
              'You can edit groups under "Dungeons".')
        )

    def get_icon(self) -> str:
        return None

    def get_back_illust(self) -> str:
        return 'dungeons'
