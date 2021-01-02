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
from typing import List, Optional

import cairo

from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple.module.dungeon.fixed_room_tileset_renderer.abstract import AbstractTilesetRenderer
from skytemple_files.graphics.dma.dma_drawer import DmaDrawer
from skytemple_files.graphics.dma.model import DmaType, Dma
from skytemple_files.graphics.dpc.model import Dpc, DPC_TILING_DIM
from skytemple_files.graphics.dpci.model import Dpci, DPCI_TILE_DIM
from skytemple_files.graphics.dpl.model import Dpl


class FixedFloorDrawerTileset(AbstractTilesetRenderer):

    def __init__(self, dma: Dma, dpci: Dpci, dpc: Dpc, dpl: Dpl):
        self._cached_rules = None
        self._cached_dungeon_surface = None
        self.dma = dma
        self.dpci = dpci
        self.dpc = dpc
        self.dpl = dpl
        self.dma_drawer = DmaDrawer(self.dma)
        chunks = self.dpc.chunks_to_pil(self.dpci, self.dpl.palettes, 1)
        self.single_tiles = {
            DmaType.FLOOR: self._single_tile(chunks, DmaType.FLOOR),
            DmaType.WALL: self._single_tile(chunks, DmaType.WALL),
            DmaType.WATER: self._single_tile(chunks, DmaType.WATER),
        }

    def get_background(self) -> Optional[cairo.Surface]:
        return None

    def get_dungeon(self, rules: List[List[DmaType]]) -> cairo.Surface:
        # TODO: If rules change only update the parts that need to be updated
        if rules != self._cached_rules:
            mappings = self.dma_drawer.get_mappings_for_rules(rules, treat_outside_as_wall=True, variation_index=0)
            self._cached_dungeon_surface = pil_to_cairo_surface(
                self.dma_drawer.draw(mappings, self.dpci, self.dpc, self.dpl, None)[0].convert('RGBA')
            )
            self._cached_rules = rules
        return self._cached_dungeon_surface

    def get_single_tile(self, tile: DmaType) -> cairo.Surface:
        return self.single_tiles[tile]

    def _single_tile(self, chunks, type):
        index = self.dma.get(type, False)[0]
        chunk_dim = DPC_TILING_DIM * DPCI_TILE_DIM
        return pil_to_cairo_surface(
            chunks.crop((0, index * chunk_dim, chunk_dim, index * chunk_dim + chunk_dim)).convert('RGBA')
        )
