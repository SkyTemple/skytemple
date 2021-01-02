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
from abc import ABC, abstractmethod
from typing import List


class AbstractTileGraphicsProvider(ABC):
    """Provides tile graphics for the ChunkEditor."""

    @abstractmethod
    def get_pil(self, palettes: List[List[int]], pal_idx: int):
        """Returns an image with all tiles on it (1 tile per row).
        The tiles are colored in the palette with index pal_idx."""

    @abstractmethod
    def count(self):
        """Returns the number of palettes"""
