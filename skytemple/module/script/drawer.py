#  Copyright 2020 Parakoopa
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
from enum import auto

import cairo
from gi.repository import Gtk

from skytemple.core.mapbg_util.drawer_plugin.grid import GridDrawerPlugin
from skytemple.core.mapbg_util.drawer_plugin.selection import SelectionDrawerPlugin
from skytemple_files.graphics.bpc.model import BPC_TILE_DIM
from skytemple_files.script.ssa_sse_sss.model import Ssa


class DrawerInteraction:
    NONE = auto()


class Drawer:
    def __init__(
            self, draw_area: Gtk.Widget, ssa: Ssa
    ):
        self.draw_area = draw_area

        self.ssa = ssa
        self.map_bg = None

        self.draw_tile_grid = False

        # Interaction
        self.interaction_mode = DrawerInteraction.NONE

        self.mouse_x = 99999
        self.mouse_y = 99999

        self.selection_plugin = SelectionDrawerPlugin(
            BPC_TILE_DIM, BPC_TILE_DIM, self.selection_draw_callback
        )
        self.tile_grid_plugin = GridDrawerPlugin(
            BPC_TILE_DIM, BPC_TILE_DIM,
            offset_x=-BPC_TILE_DIM / 2, offset_y=-BPC_TILE_DIM / 2
        )

        self.scale = 1

        self.drawing_is_active = False

    def start(self):
        """Start drawing on the DrawingArea"""
        self.drawing_is_active = True
        if isinstance(self.draw_area, Gtk.DrawingArea):
            self.draw_area.connect('draw', self.draw)
        self.draw_area.queue_draw()

    def draw(self, wdg, ctx: cairo.Context, do_translates=True):
        ctx.set_antialias(cairo.Antialias.NONE)
        ctx.scale(self.scale, self.scale)
        # Background
        if self.map_bg is not None:
            ctx.set_source_surface(self.map_bg, 0, 0)
            ctx.get_source().set_filter(cairo.Filter.NEAREST)
            ctx.paint()

        size_w, size_h = self.draw_area.get_size_request()
        # Selection
        self.selection_plugin.set_size(BPC_TILE_DIM, BPC_TILE_DIM)
        self.selection_plugin.draw(ctx, size_w, size_h, self.mouse_x, self.mouse_y)

        # Tile Grid
        if self.draw_tile_grid:
            self.tile_grid_plugin.draw(ctx, size_w, size_h, self.mouse_x, self.mouse_y)

    def selection_draw_callback(self, ctx: cairo.Context, x: int, y: int):
        pass  # todo

    def set_mouse_position(self, x, y):
        self.mouse_x = x
        self.mouse_y = y

    def get_interaction_mode(self):
        return self.interaction_mode

    def set_draw_tile_grid(self, v):
        self.draw_tile_grid = v

    def set_scale(self, v):
        self.scale = v
