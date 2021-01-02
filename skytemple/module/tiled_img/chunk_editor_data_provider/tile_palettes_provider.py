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


class AbstractTilePalettesProvider(ABC):
    """Provides tile palettes for the ChunkEditor."""

    @abstractmethod
    def get(self) -> List[List[int]]:
        """Returns the palettes as a list of RGB color streams."""

    @abstractmethod
    def is_palette_affected_by_animation(self, pal_idx) -> bool:
        """Returns whether or not the palette with that index is affected by animation"""

    @abstractmethod
    def animation_length(self):
        """Returns the length of the animation sequence in the palette, or 0 if no animation exists."""

    @abstractmethod
    def apply_palette_animations(self, frame: int) -> List[List[int]]:
        """Applies palette animations and returns the resulting palettes."""

    @abstractmethod
    def number_of_palettes(self):
        """How many palettes exist?"""
