"""Module that draws the main background DrawingArea and the chunks icon views"""
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
import typing
from enum import Enum, auto
from typing import List, Union, Iterable, Optional, Sequence

from gi.repository import GLib, Gtk
from gi.repository.GObject import ParamFlags
from gi.repository.Gtk import Widget
from range_typed_integers import u8

from skytemple.core.events.manager import EventManager
from skytemple.core.mapbg_util.drawer_plugin.grid import GridDrawerPlugin
from skytemple.core.mapbg_util.drawer_plugin.selection import SelectionDrawerPlugin
from skytemple.core.mapbg_util.map_tileset_overlay import MapTilesetOverlay
from skytemple.module.tiled_img.animation_context import AnimationContext
from skytemple_files.graphics.bma.protocol import BmaProtocol
import cairo

from skytemple_files.graphics.bpc import BPC_TILE_DIM
FPS = 60


class DrawerInteraction(Enum):
    NONE = auto()
    CHUNKS = auto()
    COL = auto()
    DAT = auto()


class Drawer:
    def __init__(
            self, draw_area: Widget, bma: Union[BmaProtocol, None], bpa_durations: int, pal_ani_durations: int,
            # chunks_surfaces[layer_number][chunk_idx][palette_animation_frame][frame]
            chunks_surfaces: Iterable[Iterable[Iterable[Iterable[cairo.Surface]]]]
    ):
        """
        Initialize a drawer...
        :param draw_area:  Widget to draw on.
        :param bma: Either a BMA with tile indexes or None, has to be set manually then for drawing
        :param bpa_durations: How many frames to hold a BPA animation tile
        :param chunks_surfaces: Bg controller format chunk surfaces
        """
        self.draw_area = draw_area

        self.reset(bma, bpa_durations, pal_ani_durations, chunks_surfaces)

        self.draw_chunk_grid = False
        self.draw_tile_grid = False
        self.use_pink_bg = False

        # Interaction
        self.interaction_mode = DrawerInteraction.NONE
        self.interaction_chunks_selected_id = 0
        self.interaction_col_solid = False
        self.interaction_dat_value = 0

        self.mouse_x = 99999
        self.mouse_y = 99999
        self.edited_layer = -1
        self.edited_collision = -1
        self.show_only_edited_layer = False
        self.dim_layers = False
        self.draw_collision1 = False
        self.draw_collision2 = False
        self.draw_data_layer = False

        self.selection_plugin = SelectionDrawerPlugin(BPC_TILE_DIM, BPC_TILE_DIM, self.selection_draw_callback)
        self.tile_grid_plugin = GridDrawerPlugin(BPC_TILE_DIM, BPC_TILE_DIM)
        self.chunk_grid_plugin = GridDrawerPlugin(
            BPC_TILE_DIM * self.tiling_width, BPC_TILE_DIM * self.tiling_height, color=(0.15, 0.15, 0.15, 0.25)
        )

        self.scale = 1

        self.drawing_is_active = False
    
    def reset_bma(self, bma):
        if isinstance(bma, BmaProtocol):
            self.tiling_width = bma.tiling_width
            self.tiling_height = bma.tiling_height
            self.mappings: List[Sequence[int]] = [bma.layer0, bma.layer1]  # type: ignore
            self.width_in_chunks = bma.map_width_chunks
            self.height_in_chunks = bma.map_height_chunks
            self.width_in_tiles: Optional[u8] = bma.map_width_camera
            self.height_in_tiles: Optional[u8] = bma.map_height_camera
            self.collision1 = bma.collision
            self.collision2 = bma.collision2
            self.data_layer = bma.unknown_data_block
        else:
            self.tiling_width = u8(3)
            self.tiling_height = u8(3)
            self.mappings = [[], []]
            self.width_in_chunks = u8(1)
            self.height_in_chunks = u8(1)
            self.width_in_tiles = None
            self.height_in_tiles = None
            self.collision1 = None
            self.collision2 = None
            self.data_layer = None

    # noinspection PyAttributeOutsideInit
    def reset(self, bma, bpa_durations, pal_ani_durations, chunks_surfaces):
        self.reset_bma(bma)

        self.animation_context = AnimationContext(chunks_surfaces, bpa_durations, pal_ani_durations)
        self._tileset_drawer_overlay: Optional[MapTilesetOverlay] = None

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
        chunk_width = self.tiling_width * BPC_TILE_DIM
        chunk_height = self.tiling_height * BPC_TILE_DIM
        # Background
        if not self.use_pink_bg:
            ctx.set_source_rgb(0, 0, 0)
        else:
            ctx.set_source_rgb(1.0, 0, 1.0)
        ctx.rectangle(
            0, 0,
            self.width_in_chunks * self.tiling_width * BPC_TILE_DIM,
            self.height_in_chunks * self.tiling_height * BPC_TILE_DIM
        )
        ctx.fill()

        if self._tileset_drawer_overlay is not None and self._tileset_drawer_overlay.enabled:
            self._tileset_drawer_overlay.draw_full(ctx, self.mappings[0], self.width_in_chunks, self.height_in_chunks)
        else:
            # Layers
            for layer_idx, chunks_at_frame in enumerate(self.animation_context.current()):
                if self.show_only_edited_layer and layer_idx != self.edited_layer:
                    continue
                current_layer_mappings = self.mappings[layer_idx]
                for i, chunk_at_pos in enumerate(current_layer_mappings):
                    if 0 < chunk_at_pos < len(chunks_at_frame):
                        chunk = chunks_at_frame[chunk_at_pos]
                        ctx.set_source_surface(chunk, 0, 0)
                        ctx.get_source().set_filter(cairo.Filter.NEAREST)
                        if self.edited_layer != -1 and layer_idx > 0 and layer_idx != self.edited_layer:
                            # For Layer 1 if not the current edited: Set an alpha mask
                            ctx.paint_with_alpha(0.7)
                        else:
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

                if (self.edited_layer != -1 and layer_idx < 1 and layer_idx != self.edited_layer) \
                    or (layer_idx == 1 and self.dim_layers) \
                    or (layer_idx == 0 and self.animation_context.num_layers < 2 and self.dim_layers):
                    # For Layer 0 if not the current edited: Draw dark rectangle
                    # or for layer 1 if dim layers
                    # ...or for layer 0 if dim layers and no second layer
                    ctx.set_source_rgba(0, 0, 0, 0.5)
                    ctx.rectangle(
                        0, 0,
                        self.width_in_chunks * self.tiling_width * BPC_TILE_DIM,
                        self.height_in_chunks * self.tiling_height * BPC_TILE_DIM
                    )
                    ctx.fill()

        # Col 1 and 2
        for col_index, should_draw in enumerate([self.draw_collision1, self.draw_collision2]):
            if should_draw:
                if col_index == 0:
                    ctx.set_source_rgba(1, 0, 0, 0.4)
                    col: Sequence[bool] = self.collision1  # type: ignore
                else:
                    ctx.set_source_rgba(0, 1, 0, 0.4)
                    col = self.collision2  # type: ignore

                for i, c in enumerate(col):
                    if c:
                        ctx.rectangle(
                            0, 0,
                            BPC_TILE_DIM,
                            BPC_TILE_DIM
                        )
                        ctx.fill()
                    if (i + 1) % self.width_in_tiles == 0:  # type: ignore
                        # Move to beginning of next line
                        if do_translates:
                            ctx.translate(-BPC_TILE_DIM * (self.width_in_tiles - 1), BPC_TILE_DIM)  # type: ignore
                    else:
                        # Move to next tile in line
                        if do_translates:
                            ctx.translate(BPC_TILE_DIM, 0)
                # Move back to beginning
                if do_translates:
                    ctx.translate(0, -BPC_TILE_DIM * self.height_in_tiles)  # type: ignore

        # Data
        if self.draw_data_layer:
            ctx.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            ctx.set_font_size(6)
            ctx.set_source_rgb(0, 0, 1)
            assert self.data_layer is not None
            for i, dat in enumerate(self.data_layer):
                if dat > 0:
                    ctx.move_to(0, BPC_TILE_DIM - 2)
                    ctx.show_text(f"{dat:02x}")
                if (i + 1) % self.width_in_tiles == 0:  # type: ignore
                    # Move to beginning of next line
                    if do_translates:
                        ctx.translate(-BPC_TILE_DIM * (self.width_in_tiles - 1), BPC_TILE_DIM)  # type: ignore
                else:
                    # Move to next tile in line
                    if do_translates:
                        ctx.translate(BPC_TILE_DIM, 0)
            # Move back to beginning
            if do_translates:
                ctx.translate(0, -BPC_TILE_DIM * self.height_in_tiles)  # type: ignore

        size_w, size_h = self.draw_area.get_size_request()
        assert size_w is not None and size_h is not None

        size_w //= self.scale
        size_h //= self.scale
        # Selection
        if self.interaction_mode == DrawerInteraction.CHUNKS:
            self.selection_plugin.set_size(self.tiling_width * BPC_TILE_DIM, self.tiling_height * BPC_TILE_DIM)
        else:
            self.selection_plugin.set_size(BPC_TILE_DIM, BPC_TILE_DIM)
        self.selection_plugin.draw(ctx, size_w, size_h, self.mouse_x, self.mouse_y)

        # Tile Grid
        if self.draw_tile_grid:
            self.tile_grid_plugin.draw(ctx, size_w, size_h, self.mouse_x, self.mouse_y)

        # Chunk Grid
        if self.draw_chunk_grid:
            self.chunk_grid_plugin.draw(ctx, size_w, size_h, self.mouse_x, self.mouse_y)
        return True

    def selection_draw_callback(self, ctx: cairo.Context, x: int, y: int):
        if self.interaction_mode == DrawerInteraction.CHUNKS:
            # Draw a chunk
            chunks_at_frame = self.animation_context.current()[self.edited_layer]
            ctx.set_source_surface(
                chunks_at_frame[self.interaction_chunks_selected_id], x, y
            )
            ctx.get_source().set_filter(cairo.Filter.NEAREST)
            ctx.paint()
        elif self.interaction_mode == DrawerInteraction.COL:
            # Draw collision
            if self.interaction_col_solid:
                ctx.set_source_rgba(1, 0, 0, 1)
                ctx.rectangle(
                    x, y,
                    BPC_TILE_DIM,
                    BPC_TILE_DIM
                )
                ctx.fill()
        elif self.interaction_mode == DrawerInteraction.DAT:
            # Draw data
            if self.interaction_dat_value > 0:
                ctx.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
                ctx.set_font_size(6)
                ctx.set_source_rgb(1, 1, 1)
                ctx.move_to(x, y + BPC_TILE_DIM - 2)
                ctx.show_text(f"{self.interaction_dat_value:02x}")

    def set_mouse_position(self, x, y):
        self.mouse_x = x
        self.mouse_y = y

    def set_selected_chunk(self, chunk_id):
        self.interaction_chunks_selected_id = chunk_id

    def get_selected_chunk_id(self):
        return self.interaction_chunks_selected_id

    def set_interaction_col_solid(self, v):
        self.interaction_col_solid = v

    def get_interaction_col_solid(self):
        return self.interaction_col_solid

    def set_interaction_dat_value(self, v):
        self.interaction_dat_value = v

    def get_interaction_dat_value(self):
        return self.interaction_dat_value

    def set_edited_layer(self, layer_id):
        # The layer that is not edited will be drawn with a bit of transparency or darker
        # Default is -1, which shows all at full opacity
        self.dim_layers = False
        self.edited_layer = layer_id
        self.draw_collision1 = False
        self.draw_collision2 = False
        self.draw_data_layer = False
        self.edited_collision = -1
        self.interaction_mode = DrawerInteraction.CHUNKS

    def set_show_only_edited_layer(self, v):
        self.show_only_edited_layer = v

    def set_edited_collision(self, collision_id):
        self.dim_layers = True
        self.edited_layer = -1
        self.draw_collision1 = False
        self.draw_collision2 = False
        self.draw_data_layer = False
        if collision_id == 0:
            self.draw_collision1 = True
        elif collision_id == 1:
            self.draw_collision2 = True
        self.edited_collision = collision_id
        self.interaction_mode = DrawerInteraction.COL

    def get_edited_collision(self):
        return self.edited_collision

    def set_edit_data_layer(self):
        self.dim_layers = True
        self.edited_layer = -1
        self.edited_collision = -1
        self.draw_collision1 = False
        self.draw_collision2 = False
        self.draw_data_layer = True
        self.interaction_mode = DrawerInteraction.DAT

    def get_interaction_mode(self):
        return self.interaction_mode

    def set_draw_chunk_grid(self, v):
        self.draw_chunk_grid = v

    def set_draw_tile_grid(self, v):
        self.draw_tile_grid = v

    def set_pink_bg(self, v):
        self.use_pink_bg = v

    def set_scale(self, v):
        self.scale = v

    def add_overlay(self, tileset_drawer_overlay):
        self._tileset_drawer_overlay = tileset_drawer_overlay

    @typing.no_type_check
    def unload(self):
        self.draw_area = None
        self.reset(None, None, None, None)
        self.draw_chunk_grid = False
        self.draw_tile_grid = False
        self.use_pink_bg = False
        self.interaction_mode = DrawerInteraction.NONE
        self.interaction_chunks_selected_id = 0
        self.interaction_col_solid = False
        self.interaction_dat_value = 0
        self.mouse_x = 99999
        self.mouse_y = 99999
        self.edited_layer = -1
        self.edited_collision = -1
        self.show_only_edited_layer = False
        self.dim_layers = False
        self.draw_collision1 = False
        self.draw_collision2 = False
        self.draw_data_layer = False
        self.selection_plugin = None
        self.tile_grid_plugin = None
        self.chunk_grid_plugin = None
        self.scale = 1
        self.drawing_is_active = False


class DrawerCellRenderer(Drawer, Gtk.CellRenderer):
    __gproperties__ = {
        'chunkidx': (int, "", "", 0, 999999, 0, ParamFlags.READWRITE)
    }

    def __init__(self, icon_view, layer: int, bpa_durations: int, pal_ani_durations: int,
                 chunks_surfaces: Iterable[Iterable[Iterable[Iterable[cairo.Surface]]]]):

        super().__init__(icon_view, None, bpa_durations, pal_ani_durations, chunks_surfaces)
        super(Gtk.CellRenderer, self).__init__()
        self.layer = layer

        self.chunkidx = 0

    def do_get_size(self, widget, cell_area):
        return 0, 0, int(BPC_TILE_DIM * 3 * self.scale), int(BPC_TILE_DIM * 3 * self.scale)

    def do_set_property(self, pspec, value):
        setattr(self, pspec.name, value)

    def do_get_property(self, pspec):
        return getattr(self, pspec.name)

    def do_render(self, ctx, wdg, background_area, cell_area, flags):
        ctx.translate(cell_area.x, cell_area.y)
        self.mappings = [[self.chunkidx], []] if self.layer < 1 else [[], [self.chunkidx]]
        self.draw(wdg, ctx, False)
        if 'GTK_CELL_RENDERER_SELECTED' in str(flags):
            ctx.set_source_rgba(0, 0, 90, 0.3)
            ctx.rectangle(
                0, 0,
                self.width_in_chunks * self.tiling_width * BPC_TILE_DIM,
                self.height_in_chunks * self.tiling_height * BPC_TILE_DIM
            )
            ctx.fill()
        ctx.translate(-cell_area.x, -cell_area.y)
