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

from skytemple.module.tiled_img.chunk_editor_data_provider.tile_palettes_provider import AbstractTilePalettesProvider
from skytemple_files.graphics.bpl.model import Bpl


class MapBgPaletteProvider(AbstractTilePalettesProvider):
    def __init__(self, bpl: Bpl):
        self.bpl = bpl

    def get(self) -> List[List[int]]:
        return self.bpl.palettes

    def is_palette_affected_by_animation(self, pal_idx) -> bool:
        return self.bpl.is_palette_affected_by_animation(pal_idx)

    def animation_length(self):
        return len(self.bpl.animation_palette)

    def apply_palette_animations(self, frame: int) -> List[List[int]]:
        return self.bpl.apply_palette_animations(frame)

    def number_of_palettes(self):
        return 16
