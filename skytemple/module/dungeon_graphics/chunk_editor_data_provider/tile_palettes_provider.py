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
from skytemple_files.common.util import lcm
from skytemple_files.graphics.bpl.model import Bpl
from skytemple.module.tiled_img.chunk_editor_data_provider.tile_palettes_provider import AbstractTilePalettesProvider
from skytemple_files.graphics.dpl.model import Dpl
from skytemple_files.graphics.dpla.model import Dpla


class DungeonPalettesProvider(AbstractTilePalettesProvider):
    def __init__(self, dpl: Dpl, dpla: Dpla):
        self.dpl = dpl
        self.dpla = dpla

    def get(self) -> List[List[int]]:
        return self.dpl.palettes

    def is_palette_affected_by_animation(self, pal_idx) -> bool:
        return pal_idx >= 10 and self.dpla.has_for_palette(pal_idx - 10)

    def animation_length(self):
        ani_pal_lengths = [self.dpla.get_frame_count_for_palette(x) for x in (0, 1) if self.dpla.has_for_palette(x)]
        if len(ani_pal_lengths) < 1:
            return 0
        if len(ani_pal_lengths) < 2:
            len_pal_ani = ani_pal_lengths[0]
        else:
            len_pal_ani = lcm(*ani_pal_lengths)
        return len_pal_ani

    def apply_palette_animations(self, frame: int) -> List[List[int]]:
        return self.dpla.apply_palette_animations(self.dpl.palettes, frame)

    def number_of_palettes(self):
        return 12
