"""
Module that draws the icon views and drawing areas in the chunk editor.
Tile based instead of chunk based.
"""
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

from typing import List, Union

from gi.repository import GLib, Gtk
from gi.repository.GObject import ParamFlags
from gi.repository.Gtk import Widget

from skytemple.core.events.manager import EventManager
from skytemple.module.tiled_img.animation_context import AnimationContext
from skytemple_files.common.tiled_image import TilemapEntry
import cairo

from skytemple_files.graphics.bpc.model import BPC_TILE_DIM
from skytemple_files.common.i18n_util import f, _

FPS = 60
FRAME_COUNTER_MAX = 1000000


class DrawerTiled:
    def __init__(
            self, draw_area: Widget, tile_mappings: Union[None, List[TilemapEntry]],
            bpa_durations: int, pal_ani_durations: int,
            # Format: tile_surfaces[pal][tile_idx][pal_frame][frame]
            tile_surfaces: List[List[List[List[cairo.Surface]]]]
    ):
        """

        :param draw_area: Widget to draw on
        :param tile_mappings: Either one tile or 3x3 tiles to draw. Can also be set later
        :param bpa_durations:
        :param tile_surfaces: List of all surfaces
        """
        self.draw_area = draw_area

        self.tile_mappings = tile_mappings

        self.tiling_width = 3
        self.tiling_height = 3

        if tile_mappings:
            self.set_tile_mappings(tile_mappings)

        self.animation_context = AnimationContext(tile_surfaces, bpa_durations, pal_ani_durations)

        self.scale = 1

        self.drawing_is_active = False

    def set_tile_mappings(self, tile_mappings):
        self.tile_mappings = tile_mappings
        if len(self.tile_mappings) == 1:
            self.width = BPC_TILE_DIM
            self.height = BPC_TILE_DIM
        elif len(self.tile_mappings) == self.tiling_width * self.tiling_height:
            self.width = BPC_TILE_DIM * self.tiling_width
            self.height = BPC_TILE_DIM * self.tiling_height
        else:
            raise ValueError(_("Only 1x1 or 3x3 supported."))

    def start(self):
        """Start drawing on the DrawingArea"""
        self.drawing_is_active = True
        if isinstance(self.draw_area, Gtk.DrawingArea):
            self.draw_area.connect('draw', self.draw)
        self.draw_area.queue_draw()
        GLib.timeout_add(int(1000 / FPS), self._tick)

    def stop(self):
        self.drawing_is_active = False

    def _tick(self):
        if self.draw_area is None:
            return False
        if self.draw_area is not None and self.draw_area.get_parent() is None:
            # XXX: Gtk doesn't remove the widget on switch sometimes...
            self.draw_area.destroy()
            return False
        self.animation_context.advance()
        if EventManager.instance().get_if_main_window_has_fous():
            self.draw_area.queue_draw()
        return self.drawing_is_active

    def draw(self, wdg, ctx: cairo.Context):
        ctx.set_antialias(cairo.Antialias.NONE)
        ctx.scale(self.scale, self.scale)

        # Background
        ctx.set_source_rgb(0, 0, 0)
        ctx.rectangle(
            0, 0,
            self.width, self.height
        )
        ctx.fill()

        matrix_x_flip = cairo.Matrix(-1, 0, 0, 1, BPC_TILE_DIM, 0)
        matrix_y_flip = cairo.Matrix(1, 0, 0, -1, 0, BPC_TILE_DIM)
        tiles_for_pals = self.animation_context.current()
        for i, mapping in enumerate(self.tile_mappings):
            tiles_for_frame = tiles_for_pals[mapping.pal_idx]
            tile_at_pos = mapping.idx
            if 0 < tile_at_pos < len(tiles_for_frame):
                tile = tiles_for_frame[tile_at_pos]
                if mapping.flip_x:
                    ctx.transform(matrix_x_flip)
                if mapping.flip_y:
                    ctx.transform(matrix_y_flip)
                ctx.set_source_surface(tile, 0, 0)
                ctx.get_source().set_filter(cairo.Filter.NEAREST)
                ctx.paint()
                if mapping.flip_x:
                    ctx.transform(matrix_x_flip)
                if mapping.flip_y:
                    ctx.transform(matrix_y_flip)
            if (i + 1) % self.tiling_width == 0:
                # Move to beginning of next line
                ctx.translate(-BPC_TILE_DIM * (self.tiling_width - 1), BPC_TILE_DIM)
            else:
                # Move to next tile in line
                ctx.translate(BPC_TILE_DIM, 0)


class DrawerTiledCellRenderer(DrawerTiled, Gtk.CellRenderer):
    __gproperties__ = {
        'tileidx': (int, "", "", 0, 999999, 0, ParamFlags.READWRITE)
    }

    def __init__(self, icon_view, bpa_durations: int, pal_ani_durations: int,
                 will_draw_chunk, all_mappings: List[TilemapEntry],
                 tile_surfaces: List[List[List[List[cairo.Surface]]]], scale):

        super().__init__(icon_view, None, bpa_durations, pal_ani_durations, tile_surfaces)
        super(Gtk.CellRenderer, self).__init__()

        self.scale = scale

        if will_draw_chunk:
            self.will_draw_chunk = True
            self.expected_dim = 3 * BPC_TILE_DIM
        else:
            self.will_draw_chunk = False
            self.expected_dim = BPC_TILE_DIM

        self.all_mappings = all_mappings
        self.tileidx = 0

    def do_get_size(self, widget, cell_area):
        return 0, 0, int(self.expected_dim * self.scale), int(self.expected_dim * self.scale)

    def do_set_property(self, pspec, value):
        setattr(self, pspec.name, value)

    def do_get_property(self, pspec):
        return getattr(self, pspec.name)

    def do_render(self, ctx, wdg, background_area, cell_area, flags):
        cell_area = self.get_aligned_area(wdg, flags, cell_area)
        ctx.translate(cell_area.x, cell_area.y)
        if self.will_draw_chunk:
            self.set_tile_mappings(self.all_mappings[self.tileidx:self.tileidx+9])
        else:
            self.set_tile_mappings([self.all_mappings[self.tileidx]])
        self.draw(wdg, ctx)
        ctx.translate(-cell_area.x, -cell_area.y)
