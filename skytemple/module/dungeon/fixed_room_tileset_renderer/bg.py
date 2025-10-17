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

import cairo
from PIL import Image

from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple.module.dungeon.fixed_room_tileset_renderer.abstract import (
    AbstractTilesetRenderer,
)
from skytemple_files.graphics.dbg.protocol import DbgProtocol
from skytemple_files.graphics.dma.dma_drawer import DmaDrawer
from skytemple_files.graphics.dma.protocol import DmaType, DmaProtocol
from skytemple_files.graphics.dpc.protocol import DpcProtocol
from skytemple_files.graphics.dpc import DPC_TILING_DIM
from skytemple_files.graphics.dpci.protocol import DpciProtocol
from skytemple_files.graphics.dpci import DPCI_TILE_DIM
from skytemple_files.graphics.dpl.protocol import DplProtocol


class FixedFloorDrawerBackground(AbstractTilesetRenderer):
    def __init__(
        self,
        dbg: DbgProtocol,
        dbg_dpci: DpciProtocol,
        dbg_dpc: DpcProtocol,
        dbg_dpl: DplProtocol,
        dma: DmaProtocol,
        chunks: Image.Image,
    ):
        self.dbg = dbg
        self.dbg_dpci = dbg_dpci
        self.dbg_dpc = dbg_dpc
        self.dbg_dpl = dbg_dpl
        self.dma = dma
        self.chunks = chunks
        self.dma_drawer = DmaDrawer(self.dma)
        self._cached_bg: cairo.ImageSurface | None = None
        self._cached_rules: list[list[int]] = []
        self._cached_dungeon_surface: cairo.ImageSurface | None = None
        self.single_tiles = {
            DmaType.FLOOR: self._single_tile(DmaType.FLOOR),
            DmaType.WALL: self._single_tile(DmaType.WALL),
            DmaType.WATER: self._single_tile(DmaType.WATER),
        }

    def get_background(self) -> cairo.Surface | None:
        if not self._cached_bg:
            self._cached_bg = pil_to_cairo_surface(
                self.dbg.to_pil(self.dbg_dpc, self.dbg_dpci, self.dbg_dpl.palettes).convert("RGBA")
            )
        return self._cached_bg

    def get_dungeon(self, rules: list[list[int]]) -> cairo.Surface:
        # TODO: If rules change only update the parts that need to be updated
        if rules != self._cached_rules:
            mappings = self.dma_drawer.get_mappings_for_rules(rules, treat_outside_as_wall=True, variation_index=0)
            self._cached_dungeon_surface = pil_to_cairo_surface(self._draw_dungeon(mappings))
            self._cached_rules = rules
        assert self._cached_dungeon_surface is not None
        return self._cached_dungeon_surface

    def get_single_tile(self, tile: int) -> cairo.Surface:
        return self.single_tiles[tile]

    def _single_tile(self, type):
        index = self.dma.get(type, False)[0]
        chunk_dim = DPC_TILING_DIM * DPCI_TILE_DIM
        chunk_width = int(self.chunks.width / chunk_dim)
        cy = int(index / chunk_width) * chunk_dim
        cx = index % chunk_width * chunk_dim
        return pil_to_cairo_surface(self.chunks.crop((cx, cy, cx + chunk_dim, cy + chunk_dim)))

    def _draw_dungeon(self, mappings: list[list[int]]) -> Image.Image:
        chunk_dim = DPCI_TILE_DIM * DPC_TILING_DIM
        chunk_width = int(self.chunks.width / chunk_dim)

        fimg = Image.new("RGBA", (len(mappings[0]) * chunk_dim, len(mappings) * chunk_dim))

        def paste(chunk_index, x, y):
            cy = int(chunk_index / chunk_width) * chunk_dim
            cx = chunk_index % chunk_width * chunk_dim
            fimg.paste(
                self.chunks.crop((cx, cy, cx + chunk_dim, cy + chunk_dim)),
                (x * chunk_dim, y * chunk_dim),
            )

        for y, row in enumerate(mappings):
            for x, cell in enumerate(row):
                paste(cell, x, y)

        return fimg
