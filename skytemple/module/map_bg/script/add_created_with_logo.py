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
import os

from skytemple.core.message_dialog import SkyTempleMessageDialog

try:
    from PIL import Image
except:
    from pil import Image
from gi.repository import Gtk

from skytemple.core.ui_utils import data_dir
from skytemple_files.common.tiled_image import from_pil
from skytemple_files.graphics.bma.model import Bma
from skytemple_files.graphics.bpc.model import Bpc, BPC_TILE_DIM
from skytemple_files.graphics.bpl.model import Bpl, BPL_IMG_PAL_LEN, BPL_MAX_PAL

PAL_OFFSET = 6


class AddCreatedWithLogo:
    """
    Add a 'Created with SkyTemple' logo to the requested map.

    - The map must be at least 22x16 chunks in size.

    The logo will be placed at 11x0 and has the size 11x8. It's placed on Layer 1,
    the tiles for it are added to the end of the BPC.
    Palettes 6 - 13 are replaced.

    Error messages are displayed with GTK.
    """
    def __init__(self, bma: Bma, bpc: Bpc, bpl: Bpl):
        self.bma = bma
        self.bpc = bpc
        self.bpl = bpl

    def process(self):
        # BPC:
        start_offset = self.bpc.layers[0].chunk_tilemap_len
        with open(os.path.join(data_dir(), 'created_with.png'), 'rb') as f:
            palettes = self._import_to_bpc(0, Image.open(f))
        # BMA:
        for x in range(0, 11):
            for y in range(0, 8):
                index = y * 11 + x % 11 + start_offset
                if index == 0:
                    index = 1
                self.bma.place_chunk(0, x + 11, y, index)
        # BPL:
        self.bpl.palettes[6:14] = palettes[0:8]

    def _error(self, error_msg):
        md = SkyTempleMessageDialog(None,
                               Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                               Gtk.ButtonsType.OK, error_msg)
        md.set_position(Gtk.WindowPosition.CENTER)
        md.run()
        md.destroy()

    def _import_to_bpc(self, layer, image):
        new_tiles, new_tilemap, palettes = from_pil(
            image, BPL_IMG_PAL_LEN, BPL_MAX_PAL, BPC_TILE_DIM,
            image.width, image.height, 3, 3
        )
        # Correct the indices of the new tilemap
        # Correct the layer mappings to use the correct palettes
        start_offset = self.bpc.layers[0].number_tiles + 1
        for m in new_tilemap:
            m.idx += start_offset
            m.pal_idx += 6
        self.bpc.layers[layer].tiles += new_tiles
        self.bpc.layers[layer].tilemap += new_tilemap

        self.bpc.layers[layer].number_tiles += len(new_tiles)
        self.bpc.layers[layer].chunk_tilemap_len += int(len(new_tilemap) / self.bpc.tiling_width / self.bpc.tiling_height)

        return palettes
