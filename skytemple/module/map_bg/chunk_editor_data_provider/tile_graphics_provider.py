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
from abc import ABC
from typing import List

from skytemple.module.tiled_img.chunk_editor_data_provider.tile_graphics_provider import AbstractTileGraphicsProvider
from skytemple_files.graphics.bpa.model import Bpa
from skytemple_files.graphics.bpc.model import Bpc


class MapBgStaticTileProvider(AbstractTileGraphicsProvider):
    def __init__(self, bpc: Bpc, layer_number: int):
        self.bpc = bpc
        self.layer_number = layer_number

    def get_pil(self, palettes: List[List[int]], pal_idx: int):
        return self.bpc.tiles_to_pil(self.layer_number, palettes, 1, pal_idx)

    def count(self):
        return len(self.bpc.layers[self.layer_number].tiles)


class MapBgAnimatedTileProvider(AbstractTileGraphicsProvider):
    def __init__(self, bpa: Bpa):
        self.bpa = bpa

    def get_pil(self, palettes: List[List[int]], pal_idx: int):
        return self.bpa.tiles_to_pil_separate(palettes[pal_idx], 1)

    def count(self):
        return self.bpa.number_of_tiles

