#  Copyright 2020-2025 SkyTemple Contributors
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

import cairo

from skytemple_files.graphics.dpc import DPC_TILING_DIM
from skytemple_files.graphics.dpci import DPCI_TILE_DIM


class AbstractTilesetRenderer(ABC):
    @abstractmethod
    def get_background(self) -> cairo.Surface | None:
        """Returns the background as a surface"""

    @abstractmethod
    def get_dungeon(self, rules: list[list[int]]) -> cairo.Surface:
        """Returns the rendered dungeon tiles for the rules."""

    @abstractmethod
    def get_single_tile(self, tile: int) -> cairo.Surface:
        """Returns a single tile image (wall/water/floor)."""

    def chunk_dim(self):
        return DPC_TILING_DIM * DPCI_TILE_DIM
