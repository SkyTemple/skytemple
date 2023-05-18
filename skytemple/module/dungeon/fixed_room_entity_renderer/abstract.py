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
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import cairo

from skytemple_files.dungeon_data.fixed_bin.model import FixedFloorActionRule
if TYPE_CHECKING:
    from skytemple.module.dungeon.fixed_room_drawer import FixedRoomDrawer


class AbstractEntityRenderer(ABC):
    def __init__(self, parent: 'FixedRoomDrawer'):
        self.parent = parent

    @abstractmethod
    def draw_action(self, ctx: cairo.Context, action: FixedFloorActionRule, sx: int, sy: int):
        pass
