"""Module that draws the main background DrawingArea and the chunks icon views for dungeon backgrounds"""
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

from typing import List, Union, Iterable

from gi.repository import GLib, Gtk
from gi.repository.GObject import ParamFlags
from gi.repository.Gtk import Widget

from skytemple.core.events.manager import EventManager
from skytemple.core.mapbg_util.drawer_plugin.grid import GridDrawerPlugin
from skytemple.core.mapbg_util.drawer_plugin.selection import SelectionDrawerPlugin
from skytemple.module.tiled_img.animation_context import AnimationContext
import cairo

from skytemple_files.graphics.dbg.model import Dbg, DBG_TILING_DIM, DBG_WIDTH_AND_HEIGHT
from skytemple_files.graphics.dpci.model import DPCI_TILE_DIM

FPS = 60


class Drawer:
    def __init__(
            self, draw_area: Widget, dbg: Union[Dbg, None], pal_ani_durations: int,
            # chunks_surfaces[chunk_idx][palette_animation_frame][frame]
            chunks_surfaces: Iterable[Iterable[List[cairo.Surface]]]
    ):
        """
        Initialize a drawer...
        :param draw_area:  Widget to draw on.
        :param dbg: Either a DBG with chunk indexes or None, has to be set manually then for drawing
        :param chunks_surfaces: Bg controller format chunk surfaces
        """
        self.draw_area = draw_area

        self.reset(dbg, pal_ani_durations, chunks_surfaces)

        self.draw_chunk_grid = True
        self.draw_tile_grid = True
        self.use_pink_bg = False

        # Interaction
        self.interaction_chunks_selected_id = 0

        self.mouse_x = 99999
        self.mouse_y = 99999

        self.tiling_width = DBG_TILING_DIM
        self.tiling_height = DBG_TILING_DIM
        self.width_in_chunks = DBG_WIDTH_AND_HEIGHT
        self.height_in_chunks = DBG_WIDTH_AND_HEIGHT
        self.width_in_tiles = DBG_WIDTH_AND_HEIGHT * 3
        self.height_in_tiles = DBG_WIDTH_AND_HEIGHT * 3

        self.selection_plugin = SelectionDrawerPlugin(DPCI_TILE_DIM, DPCI_TILE_DIM, self.selection_draw_callback)
        self.tile_grid_plugin = GridDrawerPlugin(DPCI_TILE_DIM, DPCI_TILE_DIM)
        self.chunk_grid_plugin = GridDrawerPlugin(
            DPCI_TILE_DIM * self.tiling_width, DPCI_TILE_DIM * self.tiling_height, color=(0.15, 0.15, 0.15, 0.25)
        )

        self.scale = 1

        self.drawing_is_active = False

    # noinspection PyAttributeOutsideInit
    def reset(self, dbg, pal_ani_durations, chunks_surfaces):
        if isinstance(dbg, Dbg):
            self.mappings = dbg.mappings
        else:
            self.mappings = []

        self.animation_context = AnimationContext([chunks_surfaces], 0, pal_ani_durations)

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

    def draw(self, wdg, ctx: cairo.Context, do_translates=True):
        ctx.set_antialias(cairo.Antialias.NONE)
        ctx.scale(self.scale, self.scale)
        chunk_width = self.tiling_width * DPCI_TILE_DIM
        chunk_height = self.tiling_height * DPCI_TILE_DIM
        # Background
        if not self.use_pink_bg:
            ctx.set_source_rgb(0, 0, 0)
        else:
            ctx.set_source_rgb(1.0, 0, 1.0)
        ctx.rectangle(
            0, 0,
            self.width_in_chunks * self.tiling_width * DPCI_TILE_DIM,
            self.height_in_chunks * self.tiling_height * DPCI_TILE_DIM
        )
        ctx.fill()

        # Layers
        for chunks_at_frame in self.animation_context.current():
            for i, chunk_at_pos in enumerate(self.mappings):
                if 0 < chunk_at_pos < len(chunks_at_frame):
                    chunk = chunks_at_frame[chunk_at_pos]
                    ctx.set_source_surface(chunk, 0, 0)
                    ctx.get_source().set_filter(cairo.Filter.NEAREST)
                    ctx.paint()
                if (i + 1) % self.width_in_chunks == 0:
                    # Move to beginning of next line
                    if do_translates:
                        ctx.translate(-chunk_width * (self.width_in_chunks - 1), chunk_height)
                else:
                    # Move to next tile in line
                    if do_translates:
                        ctx.translate(chunk_width, 0)

            # Move back to beginning
            if do_translates:
                ctx.translate(0, -chunk_height * self.height_in_chunks)
            break

        size_w, size_h = self.draw_area.get_size_request()
        size_w /= self.scale
        size_h /= self.scale
        # Selection
        self.selection_plugin.set_size(self.tiling_width * DPCI_TILE_DIM, self.tiling_height * DPCI_TILE_DIM)
        self.selection_plugin.draw(ctx, size_w, size_h, self.mouse_x, self.mouse_y)

        # Tile Grid
        if self.draw_tile_grid:
            self.tile_grid_plugin.draw(ctx, size_w, size_h, self.mouse_x, self.mouse_y)

        # Chunk Grid
        if self.draw_chunk_grid:
            self.chunk_grid_plugin.draw(ctx, size_w, size_h, self.mouse_x, self.mouse_y)
        return True

    def selection_draw_callback(self, ctx: cairo.Context, x: int, y: int):
        # Draw a chunk
        chunks_at_frame = self.animation_context.current()[0]
        ctx.set_source_surface(
            chunks_at_frame[self.interaction_chunks_selected_id], x, y
        )
        ctx.get_source().set_filter(cairo.Filter.NEAREST)
        ctx.paint()

    def set_mouse_position(self, x, y):
        self.mouse_x = x
        self.mouse_y = y

    def set_selected_chunk(self, chunk_id):
        self.interaction_chunks_selected_id = chunk_id

    def get_selected_chunk_id(self):
        return self.interaction_chunks_selected_id

    def set_draw_chunk_grid(self, v):
        self.draw_chunk_grid = v

    def set_draw_tile_grid(self, v):
        self.draw_tile_grid = v

    def set_pink_bg(self, v):
        self.use_pink_bg = v

    def set_scale(self, v):
        self.scale = v


class DrawerCellRenderer(Drawer, Gtk.CellRenderer):
    __gproperties__ = {
        'chunkidx': (int, "", "", 0, 999999, 0, ParamFlags.READWRITE)
    }

    def __init__(self, icon_view, pal_ani_durations: int,
                 chunks_surfaces: List[List[List[cairo.Surface]]]):

        super().__init__(icon_view, None, pal_ani_durations, chunks_surfaces)
        super(Gtk.CellRenderer, self).__init__()

        self.chunkidx = 0

    def do_get_size(self, widget, cell_area):
        return 0, 0, int(DPCI_TILE_DIM * 3 * self.scale), int(DPCI_TILE_DIM * 3 * self.scale)

    def do_set_property(self, pspec, value):
        setattr(self, pspec.name, value)

    def do_get_property(self, pspec):
        return getattr(self, pspec.name)

    def do_render(self, ctx, wdg, background_area, cell_area, flags):
        ctx.translate(cell_area.x, cell_area.y)
        self.mappings = [self.chunkidx]
        self.draw(wdg, ctx, False)
        if 'GTK_CELL_RENDERER_SELECTED' in str(flags):
            ctx.set_source_rgba(0, 0, 90, 0.3)
            ctx.rectangle(
                0, 0,
                self.width_in_chunks * self.tiling_width * DPCI_TILE_DIM,
                self.height_in_chunks * self.tiling_height * DPCI_TILE_DIM
            )
            ctx.fill()
        ctx.translate(-cell_area.x, -cell_area.y)
