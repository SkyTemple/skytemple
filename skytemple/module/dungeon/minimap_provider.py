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
import os

import cairo
from PIL import Image

from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple.core.ui_utils import data_dir
from skytemple_files.graphics.zmappat import ZMAPPAT_NB_TILES_PER_LINE
from skytemple_files.graphics.zmappat.model import ZMappaT, ZMappaTVariation
ZMAPPAT_DIM = 4


class MinimapProvider:
    def __init__(self, zmappa: ZMappaT):
        self._tiles = []
        base = zmappa.to_pil_tiles_minimized(ZMappaTVariation.OPAQUE).convert('RGBA')
        for y in range(0, 4):
            for x in range(0, ZMAPPAT_NB_TILES_PER_LINE // 2):
                self._tiles.append(pil_to_cairo_surface(base.crop(
                    (x * ZMAPPAT_DIM, y * ZMAPPAT_DIM, (x + 1) * ZMAPPAT_DIM, (y + 1) * ZMAPPAT_DIM)
                )))
        self._secondary = pil_to_cairo_surface(Image.open(os.path.join(data_dir(), 'minimap_secondary.png')))
        self._buried = pil_to_cairo_surface(Image.open(os.path.join(data_dir(), 'minimap_buried.png')))

    def get_minimap_tile(self, idx: int) -> cairo.ImageSurface:
        return self._tiles[idx]

    def get_secondary_tile(self) -> cairo.ImageSurface:
        return self._secondary

    def get_buried_item_tile(self):
        return self._buried
