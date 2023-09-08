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
from typing import List, Optional

import cairo
from PIL import Image

from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple.module.dungeon.fixed_room_tileset_renderer.abstract import AbstractTilesetRenderer
from skytemple.module.dungeon.minimap_provider import MinimapProvider, ZMAPPAT_DIM
from skytemple_files.graphics.dma.protocol import DmaType


class FixedFloorDrawerMinimap(AbstractTilesetRenderer):
    def __init__(self, minimap_provider: MinimapProvider):
        self.minimap_provider = minimap_provider
        self._cached_rules: Optional[List[List[int]]] = None
        self._cached_dungeon_surface: Optional[cairo.ImageSurface] = None

    def get_background(self) -> Optional[cairo.Surface]:
        return None

    def get_dungeon(self, rules: List[List[int]]) -> cairo.Surface:
        if rules != self._cached_rules:
            surf = pil_to_cairo_surface(Image.new(
                'RGBA', size=(len(rules[0] * ZMAPPAT_DIM), len(rules * ZMAPPAT_DIM)), color=(0, 0, 231, 255)
            ))
            ctx = cairo.Context(surf)
            for y, row in enumerate(rules):
                for x, cell in enumerate(row):
                    if cell == DmaType.WALL:
                        continue
                    self.paint(ctx, self.get_single_tile(cell), x * ZMAPPAT_DIM, y * ZMAPPAT_DIM)
                    if cell == DmaType.WATER:
                        self.paint(ctx, self.minimap_provider.get_secondary_tile(), x * ZMAPPAT_DIM, y * ZMAPPAT_DIM)
                    else:
                        w_below = self.w_below(rules, x, y)  # 0001
                        w_right = self.w_right(rules, x, y)  # 0010
                        w_above = self.w_above(rules, x, y)  # 0100
                        w_left = self.w_left(rules, x, y)    # 1000
                        idx = 16 + w_below + 2 * w_right + 4 * w_above + 8 * w_left
                        self.paint(ctx, self.minimap_provider.get_minimap_tile(idx), x * ZMAPPAT_DIM, y * ZMAPPAT_DIM)

            self._cached_dungeon_surface = surf
            self._cached_rules = rules
        assert self._cached_dungeon_surface is not None
        return self._cached_dungeon_surface

    def get_single_tile(self, tile: int) -> cairo.Surface:
        if tile == DmaType.WALL:
            return self.minimap_provider.get_minimap_tile(31)
        if tile == DmaType.FLOOR:
            return self.minimap_provider.get_minimap_tile(16)
        if tile == DmaType.WATER:
            return self.minimap_provider.get_secondary_tile()
        raise ValueError()

    def paint(self, ctx, source, x, y):
        ctx.translate(x, y)
        ctx.set_source_surface(source)
        ctx.get_source().set_filter(cairo.Filter.NEAREST)
        ctx.paint()
        ctx.translate(-x, -y)

    def w_below(self, rules: List[List[int]], x: int, y: int) -> bool:
        if y + 1 < len(rules):
            return rules[y + 1][x] != DmaType.FLOOR
        return True

    def w_right(self, rules: List[List[int]], x: int, y: int) -> bool:
        if x + 1 < len(rules[y]):
            return rules[y][x + 1] != DmaType.FLOOR
        return True

    def w_above(self, rules: List[List[int]], x: int, y: int) -> bool:
        if y - 1 >= 0:
            return rules[y - 1][x] != DmaType.FLOOR
        return True

    def w_left(self, rules: List[List[int]], x: int, y: int) -> bool:
        if x - 1 >= 0:
            return rules[y][x - 1] != DmaType.FLOOR
        return True

    def chunk_dim(self):
        return ZMAPPAT_DIM
