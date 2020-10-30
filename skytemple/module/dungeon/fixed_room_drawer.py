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
from enum import auto, Enum
from typing import Tuple, Union, Optional

import cairo
from gi.repository import Gtk

from skytemple.core.mapbg_util.drawer_plugin.grid import GridDrawerPlugin
from skytemple.core.mapbg_util.drawer_plugin.selection import SelectionDrawerPlugin
from skytemple.core.sprite_provider import SpriteProvider
from skytemple.module.dungeon.fixed_room_tileset_renderer.abstract import AbstractTilesetRenderer
from skytemple_files.dungeon_data.fixed_bin.model import FixedFloor, TileRule, TileRuleType, FloorType
from skytemple_files.graphics.dma.model import DmaType
from skytemple_files.graphics.dpc.model import DPC_TILING_DIM
from skytemple_files.graphics.dpci.model import DPCI_TILE_DIM


ALPHA_T = 0.3
Num = Union[int, float]
Color = Tuple[Num, Num, Num]
OFFSET = DPCI_TILE_DIM * DPC_TILING_DIM * 5


class InteractionMode(Enum):
    SELECT = auto()
    PLACE_TILE = auto()
    PLACE_ENTITY = auto()
    COPY = auto()


class FixedRoomDrawer:
    def __init__(
            self, draw_area: Gtk.Widget, fixed_floor: FixedFloor,
            sprite_provider: SpriteProvider
    ):
        self.draw_area = draw_area

        self.fixed_floor = fixed_floor
        self.tileset_renderer: Optional[AbstractTilesetRenderer] = None

        self.draw_tile_grid = False

        # Interaction
        self.interaction_mode = InteractionMode.SELECT
        self.mouse_x = 99999
        self.mouse_y = 99999

        self.sprite_provider = sprite_provider

        self._selected = None

        self.selection_plugin = SelectionDrawerPlugin(
            DPCI_TILE_DIM * DPC_TILING_DIM, DPCI_TILE_DIM * DPC_TILING_DIM, self.selection_draw_callback
        )
        self.tile_grid_plugin = GridDrawerPlugin(
            DPCI_TILE_DIM * DPC_TILING_DIM, DPCI_TILE_DIM * DPC_TILING_DIM,
            offset_x=OFFSET, offset_y=OFFSET
        )

        self.scale = 1

        self.drawing_is_active = False

    def start(self):
        """Start drawing on the DrawingArea"""
        self.drawing_is_active = True
        if isinstance(self.draw_area, Gtk.DrawingArea):
            self.draw_area.connect('draw', self.draw)
        self.draw_area.queue_draw()

    def draw(self, wdg, ctx: cairo.Context):
        ctx.set_antialias(cairo.Antialias.NONE)
        ctx.scale(self.scale, self.scale)
        # Background
        if self.tileset_renderer is not None:
            bg = self.tileset_renderer.get_background()
            if bg is not None:
                ctx.set_source_surface(bg, 0, 0)
                ctx.get_source().set_filter(cairo.Filter.NEAREST)
                ctx.paint()

        size_w, size_h = self.draw_area.get_size_request()
        size_w /= self.scale
        size_h /= self.scale

        # Black out bg a bit
        ctx.set_source_rgba(0, 0, 0, 0.5)
        ctx.rectangle(0, 0, size_w, size_h)
        ctx.fill()

        # Iterate over floor and render it
        draw_outside_as_second_terrain = any(action.tr_type == TileRuleType.SECONDARY_HALLWAY_VOID_ALL
                                             for action in self.fixed_floor.actions if isinstance(action, TileRule))
        outside = DmaType.WATER if draw_outside_as_second_terrain else DmaType.WALL
        rules = []
        rules.append([outside] * (self.fixed_floor.width + 10))
        rules.append([outside] * (self.fixed_floor.width + 10))
        rules.append([outside] * (self.fixed_floor.width + 10))
        rules.append([outside] * (self.fixed_floor.width + 10))
        rules.append([outside] * (self.fixed_floor.width + 10))
        ridx = 0
        for y in range(0, self.fixed_floor.height):
            row = [outside, outside, outside, outside, outside]
            rules.append(row)
            for x in range(0, self.fixed_floor.width):
                action = self.fixed_floor.actions[ridx]
                if isinstance(action, TileRule):
                    if action.tr_type.floor_type == FloorType.FLOOR:
                        row.append(DmaType.FLOOR)
                    elif action.tr_type.floor_type == FloorType.WALL:
                        row.append(DmaType.WALL)
                    elif action.tr_type.floor_type == FloorType.SECONDARY:
                        row.append(DmaType.WATER)
                    elif action.tr_type.floor_type == FloorType.FLOOR_OR_WALL:
                        row.append(DmaType.WALL)
                else:
                    row.append(DmaType.FLOOR)
                ridx += 1
            row += [outside, outside, outside, outside, outside]
        rules.append([outside] * (self.fixed_floor.width + 10))
        rules.append([outside] * (self.fixed_floor.width + 10))
        rules.append([outside] * (self.fixed_floor.width + 10))
        rules.append([outside] * (self.fixed_floor.width + 10))
        rules.append([outside] * (self.fixed_floor.width + 10))

        dungeon = self.tileset_renderer.get_dungeon(rules)
        ctx.set_source_surface(dungeon, 0, 0)
        ctx.get_source().set_filter(cairo.Filter.NEAREST)
        ctx.paint()

        # Tile Grid
        if self.draw_tile_grid:
            self.tile_grid_plugin.draw(ctx, size_w - OFFSET, size_h - OFFSET, self.mouse_x, self.mouse_y)

        # TODO: Draw Pokémon, items, traps, etc.

        # Cursor / Active selected / Place mode
        #self._handle_selection(ctx)
        x, y, w, h = self.mouse_x, self.mouse_y, DPCI_TILE_DIM * DPC_TILING_DIM, DPCI_TILE_DIM * DPC_TILING_DIM
        self.selection_plugin.set_size(w, h)
        self.selection_plugin.draw(ctx, size_w, size_h, x, y, ignore_obb=True)
        return True

    def selection_draw_callback(self, ctx: cairo.Context, x: int, y: int):
        pass

    def set_mouse_position(self, x, y):
        self.mouse_x = x
        self.mouse_y = y

    def set_draw_tile_grid(self, v):
        self.draw_tile_grid = v

    def set_scale(self, v):
        self.scale = v

    def set_tileset_renderer(self, renderer: AbstractTilesetRenderer):
        self.tileset_renderer = renderer

    def _redraw(self):
        if self.draw_area is None or self.draw_area.get_parent() is None:
            return
        self.draw_area.queue_draw()
