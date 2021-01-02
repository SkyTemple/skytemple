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
from typing import List, Iterable, Optional

import cairo
FRAME_COUNTER_MAX = 1000000


class AnimationContext:
    """This class can draw animated backgrounds using palette and frame animations."""
    # TODO: No BPAs at different speeds supported at the moment
    # TODO: No BPL animations at different speeds supported at the moment
    def __init__(
        self,
        # [collection_idx][tile_or_chunk_idx][palette_animation_frame][frame]
        surfaces: List[List[List[List[cairo.Surface]]]],
        bpa_durations: int,
        pal_ani_durations: int
    ):
        self.surfaces = surfaces
        self.bpa_durations = bpa_durations
        self.pal_ani_durations = pal_ani_durations

        # This counts up the current frame index for BPA and PAL animations, up to FRAME_COUNTER_MAX,
        # then it resets to 0. Use the % operator to get the current element in the nested lists, as
        # their sub-list lengths may vary (eg. not all tiles have the same frame number for
        # BPA animation or palette animation)
        self._bpa_counter = 0
        self._pal_counter = 0

        # The current pal_ani/bpa_ani frame numbers as tuple. This is the current cache "hash"!
        self._current_cache_hash = (None, None)
        # The current cached surfaces for each collection:
        self._current_cache: List[List[cairo.Surface]] = []

        self.frame_counter = 0

    @property
    def num_layers(self) -> int:
        return len(self.surfaces)

    def current(self) -> List[List[cairo.Surface]]:
        """Returns the surfaces for this frame"""
        if (self._pal_counter, self._bpa_counter) == self._current_cache_hash:
            return self._current_cache

        self._current_cache = []
        for collection_idx, collection in enumerate(self.surfaces):
            # The surfaces for this collection, for this frame:
            collection_surfaces: List[cairo.Surface] = []
            for tile_idx, pal_ani_frames in enumerate(collection):
                bpa_ani_frames = pal_ani_frames[self._pal_counter % len(pal_ani_frames)]
                surf = bpa_ani_frames[self._bpa_counter % len(bpa_ani_frames)]
                collection_surfaces.append(surf)
            self._current_cache.append(collection_surfaces)
        self._current_cache_hash = (self._pal_counter, self._bpa_counter)
        return self._current_cache

    def advance(self):
        # Advance frame if enough time passed
        if self.bpa_durations > 0:
            if self.frame_counter % self.bpa_durations == 0:
                self._bpa_counter += 1
                if self._bpa_counter > FRAME_COUNTER_MAX:
                    self._bpa_counter = 0

        if self.pal_ani_durations > 0:
            if self.frame_counter % self.pal_ani_durations == 0:
                self._pal_counter += 1
                if self._pal_counter > FRAME_COUNTER_MAX:
                    self._pal_counter = 0

        self.frame_counter += 1
        if self.frame_counter > FRAME_COUNTER_MAX:
            self.frame_counter = 0
