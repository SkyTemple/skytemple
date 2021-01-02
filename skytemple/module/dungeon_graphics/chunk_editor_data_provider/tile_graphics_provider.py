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
from typing import List

from skytemple.module.tiled_img.chunk_editor_data_provider.tile_graphics_provider import AbstractTileGraphicsProvider
from skytemple_files.graphics.dpci.model import Dpci


class DungeonTilesProvider(AbstractTileGraphicsProvider):
    def __init__(self, dpci: Dpci):
        self.dpci = dpci

    def get_pil(self, palettes: List[List[int]], pal_idx: int):
        return self.dpci.tiles_to_pil(palettes, 1, pal_idx)

    def count(self):
        return len(self.dpci.tiles)
