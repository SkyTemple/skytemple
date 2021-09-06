#  Copyright 2020-2021 Capypara and the SkyTemple Contributors
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
from typing import Optional, List

import cairo

from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple_files.dungeon_data.fixed_bin.model import FixedFloor
from skytemple_files.graphics.bpc.model import BPC_TILE_DIM
from skytemple_files.graphics.dma.dma_drawer import DmaDrawer
from skytemple_files.graphics.dma.model import Dma
from skytemple_files.graphics.dpc.model import Dpc
from skytemple_files.graphics.dpci.model import Dpci
from skytemple_files.graphics.dpl.model import Dpl


class MapTilesetOverlay:
    """Drawer overlay for rendering mode 10 or 11 ground maps using dungeon tiles and/or fixed rooms."""
    def __init__(self, dma: Dma, dpc: Dpc, dpci: Dpci, dpl: Dpl, fixed_room: Optional[FixedFloor]):
        self.dma = dma
        self.dpc = dpc
        self.dpci = dpci
        self.dpl = dpl
        self.fixed_room = fixed_room
        self.enabled = True
        self._cached = None
        self._cached__bma_chunk_width = None
        self._cached__bma_chunks = None

    def draw_full(self, ctx: cairo.Context, bma_chunks: List[int], bma_chunk_width: int, bma_chunk_height: int):
        if bma_chunk_width != self._cached__bma_chunk_width or self._cached__bma_chunks != bma_chunks:
            self._cached__bma_chunk_width = bma_chunk_width
            self._cached__bma_chunks = list(bma_chunks)
            self._cached = None
        if self._cached is None:
            drawer = DmaDrawer(self.dma)
            if self.fixed_room:
                rules = drawer.rules_from_fixed_room(self.fixed_room)
            else:
                rules = drawer.rules_from_bma(bma_chunks, bma_chunk_width)
            mappings = drawer.get_mappings_for_rules(rules, treat_outside_as_wall=True, variation_index=0)
            frame = pil_to_cairo_surface(drawer.draw(mappings, self.dpci, self.dpc, self.dpl, None)[0].convert('RGBA'))
            self._cached = frame
        ctx.set_source_surface(self._cached)
        ctx.get_source().set_filter(cairo.Filter.NEAREST)
        ctx.paint()

    def create(self, bma_chunks: List[int], bma_chunk_width: int, bma_chunk_height: int) -> cairo.Surface:
        surface = cairo.ImageSurface(cairo.FORMAT_RGB24,
                                     bma_chunk_width * BPC_TILE_DIM * 3, bma_chunk_height * BPC_TILE_DIM * 3)
        self.draw_full(cairo.Context(surface), bma_chunks, bma_chunk_width, bma_chunk_height)
        return surface
