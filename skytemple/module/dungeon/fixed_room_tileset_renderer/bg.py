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
from PIL import Image

from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple.module.dungeon.fixed_room_tileset_renderer.abstract import AbstractTilesetRenderer
from skytemple_files.graphics.dbg.model import Dbg
from skytemple_files.graphics.dma.dma_drawer import DmaDrawer
from skytemple_files.graphics.dma.model import DmaType, Dma
from skytemple_files.graphics.dpc.model import Dpc, DPC_TILING_DIM
from skytemple_files.graphics.dpci.model import Dpci, DPCI_TILE_DIM
from skytemple_files.graphics.dpl.model import Dpl


class FixedFloorDrawerBackground(AbstractTilesetRenderer):
    def __init__(self, dbg: Dbg, dbg_dpci: Dpci, dbg_dpc: Dpc, dbg_dpl: Dpl, dma: Dma, chunks: Image.Image):
        self.dbg = dbg
        self.dbg_dpci = dbg_dpci
        self.dbg_dpc = dbg_dpc
        self.dbg_dpl = dbg_dpl
        self.dma = dma
        self.chunks = chunks
        self.dma_drawer = DmaDrawer(self.dma)
        self._cached_bg = None
        self._cached_rules = None
        self._cached_dungeon_surface = None
        self.single_tiles = {
            DmaType.FLOOR: self._single_tile(DmaType.FLOOR),
            DmaType.WALL: self._single_tile(DmaType.WALL),
            DmaType.WATER: self._single_tile(DmaType.WATER),
        }

    def get_background(self) -> Optional[cairo.Surface]:
        if not self._cached_bg:
            self._cached_bg = pil_to_cairo_surface(
                self.dbg.to_pil(self.dbg_dpc, self.dbg_dpci, self.dbg_dpl.palettes).convert('RGBA')
            )
        return self._cached_bg

    def get_dungeon(self, rules: List[List[DmaType]]) -> cairo.Surface:
        # TODO: If rules change only update the parts that need to be updated
        if rules != self._cached_rules:
            mappings = self.dma_drawer.get_mappings_for_rules(rules, treat_outside_as_wall=True, variation_index=0)
            self._cached_dungeon_surface = pil_to_cairo_surface(
                self._draw_dungeon(mappings)
            )
            self._cached_rules = rules
        return self._cached_dungeon_surface

    def get_single_tile(self, tile: DmaType) -> cairo.Surface:
        return self.single_tiles[tile]

    def _single_tile(self, type):
        index = self.dma.get(type, False)[0]
        chunk_dim = DPC_TILING_DIM * DPCI_TILE_DIM
        chunk_width = int(self.chunks.width / chunk_dim)
        cy = int(index / chunk_width) * chunk_dim
        cx = index % chunk_width * chunk_dim
        return pil_to_cairo_surface(
            self.chunks.crop((cx, cy, cx + chunk_dim, cy + chunk_dim))
        )

    def _draw_dungeon(self, mappings: List[List[int]]) -> Image.Image:
        chunk_dim = DPCI_TILE_DIM * DPC_TILING_DIM
        chunk_width = int(self.chunks.width / chunk_dim)

        fimg = Image.new('RGBA', (len(mappings[0]) * chunk_dim, len(mappings) * chunk_dim))

        def paste(chunk_index, x, y):
            cy = int(chunk_index / chunk_width) * chunk_dim
            cx = chunk_index % chunk_width * chunk_dim
            fimg.paste(
                self.chunks.crop((cx, cy, cx + chunk_dim, cy + chunk_dim)),
                (x * chunk_dim, y * chunk_dim)
            )

        for y, row in enumerate(mappings):
            for x, cell in enumerate(row):
                paste(cell, x, y)

        return fimg
