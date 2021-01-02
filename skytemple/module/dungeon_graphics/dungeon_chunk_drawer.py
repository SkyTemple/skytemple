"""Module that draws the chunks icon views"""
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

from typing import List, Iterable

from gi.repository import GLib, Gtk
from gi.repository.GObject import ParamFlags
from gi.repository.Gtk import Widget

from skytemple.core.events.manager import EventManager
from skytemple.module.tiled_img.animation_context import AnimationContext
import cairo

from skytemple_files.graphics.dpc.model import DPC_TILING_DIM
from skytemple_files.graphics.dpci.model import DPCI_TILE_DIM
FPS = 60


class DungeonChunkDrawer:
    def __init__(
            self, draw_area: Widget, pal_ani_durations: int,
            # chunks_surfaces[chunk_idx][palette_animation_frame][frame]
            # Since we only have static tiles, frames should always only contain one element.
            chunks_surfaces: Iterable[Iterable[List[cairo.Surface]]]
    ):
        """
        Initialize a drawer...
        :param draw_area:  Widget to draw on.
        :param pal_ani_durations: How many frames to hold a palette animation.
        :param chunks_surfaces: Bg controller format chunk surfaces
        """
        self.draw_area = draw_area

        self.reset(pal_ani_durations, chunks_surfaces)

        self.scale = 2

        self.drawing_is_active = False

    # noinspection PyAttributeOutsideInit
    def reset(self, pal_ani_durations, chunks_surfaces):
        # Chunk to draw
        self.chunkidx = 0
        self.pal_ani_durations = pal_ani_durations
        self.reset_surfaces(chunks_surfaces)

    # noinspection PyAttributeOutsideInit
    def reset_surfaces(self, chunks_surfaces):
        self.animation_context = AnimationContext([chunks_surfaces], 1, self.pal_ani_durations)

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

        chunks_at_frame = self.animation_context.current()[0]
        if 0 <= self.chunkidx < len(chunks_at_frame):
            chunk = chunks_at_frame[self.chunkidx]
            ctx.set_source_surface(chunk, 0, 0)
            ctx.get_source().set_filter(cairo.Filter.NEAREST)
            ctx.paint()

    def set_scale(self, v):
        self.scale = v


class DungeonChunkCellDrawer(DungeonChunkDrawer, Gtk.CellRenderer):
    __gproperties__ = {
        'chunkidx': (int, "", "", 0, 999999, 0, ParamFlags.READWRITE)
    }

    def __init__(self, icon_view, pal_ani_durations: int,
                 chunks_surfaces: Iterable[Iterable[List[cairo.Surface]]], selection_draw_solid):

        super().__init__(icon_view, pal_ani_durations, chunks_surfaces)
        super(Gtk.CellRenderer, self).__init__()
        self.selection_draw_solid = selection_draw_solid

    def do_get_size(self, widget, cell_area):
        return 0, 0, int(DPCI_TILE_DIM * 3 * self.scale), int(DPCI_TILE_DIM * 3 * self.scale)

    def do_set_property(self, pspec, value):
        setattr(self, pspec.name, value)

    def do_get_property(self, pspec):
        return getattr(self, pspec.name)

    def do_render(self, ctx, wdg, background_area, cell_area, flags):
        ctx.translate(cell_area.x, cell_area.y)
        if not self.selection_draw_solid:
            self.draw_selection(ctx, flags)
        self.draw(wdg, ctx)
        if self.selection_draw_solid:
            self.draw_selection(ctx, flags)
        ctx.translate(-cell_area.x, -cell_area.y)

    def draw_selection(self, ctx, flags):
        if 'GTK_CELL_RENDERER_SELECTED' in str(flags):
            ctx.set_source_rgba(0, 0, 90, 0.3)
            ctx.rectangle(
                0, 0,
                DPC_TILING_DIM * DPCI_TILE_DIM,
                DPC_TILING_DIM * DPCI_TILE_DIM
            )
            ctx.fill()
