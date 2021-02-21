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
import math
from enum import auto, Enum
from typing import Union, Optional, Tuple

import cairo
from gi.repository import Gtk, GLib

from skytemple.core.mapbg_util.drawer_plugin.grid import GridDrawerPlugin
from skytemple.core.mapbg_util.drawer_plugin.selection import SelectionDrawerPlugin
from skytemple.core.sprite_provider import SpriteProvider
from skytemple.core.string_provider import StringProvider, StringType
from skytemple.module.dungeon import MAX_ITEMS
from skytemple.module.dungeon.entity_rule_container import EntityRuleContainer
from skytemple.module.dungeon.fixed_room_tileset_renderer.abstract import AbstractTilesetRenderer
from skytemple_files.dungeon_data.fixed_bin.model import FixedFloor, TileRule, TileRuleType, FloorType, EntityRule, \
    RoomType, FixedFloorActionRule
from skytemple_files.dungeon_data.mappa_bin.trap_list import MappaTrapType
from skytemple_files.graphics.dma.model import DmaType
from skytemple_files.graphics.dpc.model import DPC_TILING_DIM
from skytemple_files.graphics.dpci.model import DPCI_TILE_DIM
from skytemple_files.hardcoded.fixed_floor import MonsterSpawnType
from skytemple_files.common.i18n_util import _

ALPHA_T = 0.3
Num = Union[int, float]
OFFSET = DPCI_TILE_DIM * DPC_TILING_DIM * 5
COLOR_TRAP = (0, 1, 0.3, 1)
COLOR_ITEM = (0, 0.3, 1, 1)
COLOR_OUTLINE = (0, 0, 0, 1)
COLOR_KEY_WALL = (1, 0.3, 0, 1)
COLOR_WARP_ZONE = (1, 0, 0.3, 1)
COLOR_RED = (1, 0, 0, 1)
COLOR_YELLOW = (1, 1, 0, 1)
COLOR_GREEN = (0, 1, 0, 1)
COLOR_WHITE = (1, 1, 1, 1)


class InteractionMode(Enum):
    SELECT = auto()
    PLACE_TILE = auto()
    PLACE_ENTITY = auto()
    COPY = auto()


class InfoLayer(Enum):
    TILE = auto()
    ITEM = auto()
    MONSTER = auto()
    TRAP = auto()


class FixedRoomDrawer:
    def __init__(
            self, draw_area: Gtk.Widget, fixed_floor: FixedFloor,
            sprite_provider: SpriteProvider, entity_rule_container: EntityRuleContainer,
            string_provider: StringProvider
    ):
        self.draw_area = draw_area

        self.fixed_floor = fixed_floor
        self.tileset_renderer: Optional[AbstractTilesetRenderer] = None

        self.draw_tile_grid = False
        self.info_layer_active = None
        self.entity_rule_container = entity_rule_container

        # Interaction
        self.interaction_mode = InteractionMode.SELECT
        self.mouse_x = 99999
        self.mouse_y = 99999

        self.sprite_provider = sprite_provider
        self.string_provider = string_provider

        # Depending on the mode this is either a coordinate tuple or a FixedFloorActionRule to place.
        self._selected: Optional[Union[Tuple[int, int], FixedFloorActionRule]] = None
        self._selected__drag = None

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
                    item, monster, tile, stats = self.entity_rule_container.get(action.entity_rule_id)
                    if tile.is_secondary_terrain():
                        row.append(DmaType.WATER)
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

        # Black out non-editable area
        ctx.set_source_rgba(0, 0, 0, 0.5)
        ctx.rectangle(0, 0,
                      size_w, DPCI_TILE_DIM * DPC_TILING_DIM * 5)
        ctx.fill()
        ctx.set_source_rgba(0, 0, 0, 0.5)
        ctx.rectangle(0, DPCI_TILE_DIM * DPC_TILING_DIM * (self.fixed_floor.height + 5),
                      size_w, DPCI_TILE_DIM * DPC_TILING_DIM * 5)
        ctx.fill()
        ctx.set_source_rgba(0, 0, 0, 0.5)
        ctx.rectangle(0, DPCI_TILE_DIM * DPC_TILING_DIM * 5,
                      DPCI_TILE_DIM * DPC_TILING_DIM * 5, DPCI_TILE_DIM * DPC_TILING_DIM * self.fixed_floor.height)
        ctx.fill()
        ctx.set_source_rgba(0, 0, 0, 0.5)
        ctx.rectangle(DPCI_TILE_DIM * DPC_TILING_DIM * (self.fixed_floor.width + 5), DPCI_TILE_DIM * DPC_TILING_DIM * 5,
                      DPCI_TILE_DIM * DPC_TILING_DIM * 5, DPCI_TILE_DIM * DPC_TILING_DIM * self.fixed_floor.height)
        ctx.fill()

        # Draw Pokémon, items, traps, etc.
        ridx = 0
        for y in range(0, self.fixed_floor.height):
            y += 5
            for x in range(0, self.fixed_floor.width):
                x += 5
                action = self.fixed_floor.actions[ridx]
                sx = DPCI_TILE_DIM * DPC_TILING_DIM * x
                sy = DPCI_TILE_DIM * DPC_TILING_DIM * y
                self._draw_action(ctx, action, sx, sy)
                ridx += 1

        # Draw info layer
        if self.info_layer_active:
            # Black out bg a bit
            ctx.set_source_rgba(0, 0, 0, 0.5)
            ctx.rectangle(0, 0, size_w, size_h)
            ctx.fill()
            ridx = 0
            for y in range(0, self.fixed_floor.height):
                y += 5
                for x in range(0, self.fixed_floor.width):
                    x += 5
                    action = self.fixed_floor.actions[ridx]
                    sx = DPCI_TILE_DIM * DPC_TILING_DIM * x
                    sy = DPCI_TILE_DIM * DPC_TILING_DIM * y
                    if isinstance(action, EntityRule):
                        item, monster, tile, stats = self.entity_rule_container.get(action.entity_rule_id)
                        # Has trap?
                        if tile.trap_id < 25 and self.info_layer_active == InfoLayer.TRAP:
                            self._draw_info_trap(sx, sy, ctx, self._trap_name(tile.trap_id),
                                                 tile.can_be_broken(), tile.trap_is_visible())
                        # Has item?
                        if item.item_id > 0 and self.info_layer_active == InfoLayer.ITEM:
                            self._draw_info_item(sx, sy, ctx, self._item_name(item.item_id))
                        # Has Pokémon?
                        if monster.md_idx > 0 and self.info_layer_active == InfoLayer.MONSTER:
                            self._draw_info_monster(sx, sy, ctx, monster.enemy_settings)
                        if self.info_layer_active == InfoLayer.TILE:
                            self._draw_info_tile(sx, sy, ctx, tile.room_id, False, False)
                    elif self.info_layer_active == InfoLayer.TILE:
                        self._draw_info_tile(sx, sy, ctx, 
                                             0 if action.tr_type.room_type == RoomType.ROOM else -1, 
                                             action.tr_type.impassable, action.tr_type.absolute_mover)
                    ridx += 1

        # Cursor / Active selected / Place mode
        x, y, w, h = self.mouse_x, self.mouse_y, DPCI_TILE_DIM * DPC_TILING_DIM, DPCI_TILE_DIM * DPC_TILING_DIM
        self.selection_plugin.set_size(w, h)
        xg, yg = self.get_cursor_pos_in_grid()
        xg *= DPCI_TILE_DIM * DPC_TILING_DIM
        yg *= DPCI_TILE_DIM * DPC_TILING_DIM
        self.selection_plugin.draw(ctx, size_w, size_h, xg, yg, ignore_obb=True)
        return True

    def selection_draw_callback(self, ctx: cairo.Context, x: int, y: int):
        sx = DPCI_TILE_DIM * DPC_TILING_DIM * x
        sy = DPCI_TILE_DIM * DPC_TILING_DIM * y
        if self.interaction_mode == InteractionMode.SELECT:
            if self._selected is not None and self._selected__drag is not None:
                # Draw dragged:
                selected_x, selected_y = self._selected
                selected = self.fixed_floor.actions[self.fixed_floor.width * selected_y + selected_x]
                self._draw_single_tile(ctx, selected, x, y)
                self._draw_action(ctx, selected, x, y)
        # Tool modes
        elif self.interaction_mode == InteractionMode.PLACE_TILE or self.interaction_mode == InteractionMode.PLACE_ENTITY:
            self._draw_single_tile(ctx, self._selected, x, y)
            self._draw_action(ctx, self._selected, x, y)

    def set_mouse_position(self, x, y):
        self.mouse_x = x
        self.mouse_y = y

    def end_drag(self):
        self._selected__drag = None

    def set_draw_tile_grid(self, v):
        self.draw_tile_grid = v
        self._redraw()

    def set_info_layer(self, v: Optional[InfoLayer]):
        self.info_layer_active = v
        self.draw_area.queue_draw()

    def set_scale(self, v):
        self.scale = v

    def set_tileset_renderer(self, renderer: AbstractTilesetRenderer):
        self.tileset_renderer = renderer

    def set_selected(self, selected):
        self._selected = selected
        self._redraw()

    def get_selected(self):
        return self._selected

    def set_drag_position(self, x: int, y: int):
        """Start dragging. x/y is the offset on the entity, where the dragging was started."""
        self._selected__drag = (x, y)

    def get_cursor_is_in_bounds(self, w, h, real_offset=False):
        return self.get_pos_is_in_bounds(self.mouse_x, self.mouse_y, w, h, real_offset)

    def get_cursor_pos_in_grid(self, real_offset=False):
        return self.get_pos_in_grid(self.mouse_x, self.mouse_y, real_offset)

    def get_pos_is_in_bounds(self, x, y, w, h, real_offset=False):
        x, y = self.get_pos_in_grid(x, y, real_offset)
        return x > -1 and y > - 1 and x < w and y < h

    def get_pos_in_grid(self, x, y, real_offset=False):
        x = int(x / (DPC_TILING_DIM * DPCI_TILE_DIM))
        y = int(y / (DPC_TILING_DIM * DPCI_TILE_DIM))
        if real_offset:
            x -= 5
            y -= 5
        return x, y

    def _redraw(self):
        if self.draw_area is None or self.draw_area.get_parent() is None:
            return
        self.draw_area.queue_draw()

    def _draw_placeholder(self, actor_id, sx, sy, direction, ctx):
        sprite, cx, cy, w, h = self.sprite_provider.get_actor_placeholder(
            actor_id,
            direction.ssa_id if direction is not None else 0,
            lambda: GLib.idle_add(self._redraw)
        )
        ctx.translate(sx, sy)
        ctx.set_source_surface(
            sprite,
            -cx + DPCI_TILE_DIM * DPC_TILING_DIM / 2,
            -cy + DPCI_TILE_DIM * DPC_TILING_DIM * 0.75
        )
        ctx.get_source().set_filter(cairo.Filter.NEAREST)
        ctx.paint()
        ctx.translate(-sx, -sy)

    def _draw_info_trap(self, sx, sy, ctx, name, can_be_broken, visible):
        self._draw_name(ctx, sx, sy, name, COLOR_WHITE)
        if can_be_broken:
            self._draw_bottom_left(ctx, sx, sy, COLOR_RED, 'B')
        if visible:
            self._draw_bottom_right(ctx, sx, sy, COLOR_YELLOW, 'V')

    def _draw_info_item(self, sx, sy, ctx, name):
        self._draw_name(ctx, sx, sy, name, COLOR_WHITE)

    def _draw_info_monster(self, sx, sy, ctx, enemy_settings):
        if enemy_settings == MonsterSpawnType.ALLY_HELP:
            self._draw_bottom_left(ctx, sx, sy, COLOR_GREEN, 'A')
        elif enemy_settings == MonsterSpawnType.ENEMY_STRONG:
            self._draw_bottom_left(ctx, sx, sy, COLOR_RED, 'E')
        else:
            self._draw_bottom_right(ctx, sx, sy, COLOR_YELLOW, 'O')

    def _draw_info_tile(self, sx, sy, ctx, room_id, impassable, absolute_mover):
        if room_id > -1:
            self._draw_top_right(ctx, sx, sy, COLOR_RED, str(room_id))
        if impassable:
            self._draw_bottom_left(ctx, sx, sy, COLOR_YELLOW, 'I')
        if absolute_mover:
            self._draw_bottom_right(ctx, sx, sy, COLOR_GREEN, 'A')

    def _trap_name(self, trap_id):
        return MappaTrapType(trap_id).name

    def _item_name(self, item_id):
        return self.string_provider.get_value(StringType.ITEM_NAMES, item_id) if item_id < MAX_ITEMS else _("(Special?)")

    def _draw_name(self, ctx, sx, sy, name, color):
        ctx.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_source_rgba(*color)
        ctx.set_font_size(12)
        ctx.move_to(sx, sy - 10)
        ctx.show_text(name)

    def _draw_top_right(self, ctx, sx, sy, color, text):
        self._draw_little_text(ctx, sx + 20, sy + 8, color, text)

    def _draw_bottom_left(self, ctx, sx, sy, color, text):
        self._draw_little_text(ctx, sx + 2, sy + 22, color, text)

    def _draw_bottom_right(self, ctx, sx, sy, color, text):
        self._draw_little_text(ctx, sx + 20, sy + 22, color, text)

    def _draw_little_text(self, ctx, sx, sy, color, text):
        ctx.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_source_rgba(*color)
        ctx.set_font_size(8)
        ctx.move_to(sx, sy)
        ctx.show_text(text)

    def _draw_action(self, ctx, action, sx, sy):
        if isinstance(action, EntityRule):
            item, monster, tile, stats = self.entity_rule_container.get(action.entity_rule_id)
            # Has trap?
            if tile.trap_id < 25:
                ctx.rectangle(sx + 5, sy + 5, DPCI_TILE_DIM * DPC_TILING_DIM - 10, DPCI_TILE_DIM * DPC_TILING_DIM - 10)
                ctx.set_source_rgba(*COLOR_TRAP)
                ctx.fill_preserve()
                ctx.set_source_rgba(*COLOR_OUTLINE)
                ctx.set_line_width(1)
                ctx.stroke()
            # Has item?
            if item.item_id > 0:
                ctx.arc(sx + DPCI_TILE_DIM * DPC_TILING_DIM / 2, sy + DPCI_TILE_DIM * DPC_TILING_DIM / 2,
                        DPCI_TILE_DIM * DPC_TILING_DIM / 2, 0, 2 * math.pi)
                ctx.set_source_rgba(*COLOR_ITEM)
                ctx.fill_preserve()
                ctx.set_source_rgba(*COLOR_OUTLINE)
                ctx.set_line_width(1)
                ctx.stroke()
            # Has Pokémon?
            if monster.md_idx > 0:
                sprite, cx, cy, w, h = self.sprite_provider.get_monster(
                    monster.md_idx,
                    action.direction.ssa_id if action.direction is not None else 0,
                    lambda: GLib.idle_add(self._redraw)
                )
                ctx.translate(sx, sy)
                ctx.set_source_surface(
                    sprite,
                    -cx + DPCI_TILE_DIM * DPC_TILING_DIM / 2,
                    -cy + DPCI_TILE_DIM * DPC_TILING_DIM * 0.75
                )
                ctx.get_source().set_filter(cairo.Filter.NEAREST)
                ctx.paint()
                ctx.translate(-sx, -sy)
        else:
            # Leader spawn tile
            if action.tr_type == TileRuleType.LEADER_SPAWN:
                self._draw_placeholder(0, sx, sy, action.direction, ctx)
            # Attendant1 spawn tile
            if action.tr_type == TileRuleType.ATTENDANT1_SPAWN:
                self._draw_placeholder(10, sx, sy, action.direction, ctx)
            # Attendant2 spawn tile
            if action.tr_type == TileRuleType.ATTENDANT2_SPAWN:
                self._draw_placeholder(11, sx, sy, action.direction, ctx)
            # Attendant3 spawn tile
            if action.tr_type == TileRuleType.ATTENDANT3_SPAWN:
                self._draw_placeholder(15, sx, sy, action.direction, ctx)
            # Key walls
            if action.tr_type == TileRuleType.FL_WA_ROOM_FLAG_0C or action.tr_type == TileRuleType.FL_WA_ROOM_FLAG_0D:
                ctx.rectangle(sx + 5, sy + 5, DPCI_TILE_DIM * DPC_TILING_DIM - 10, DPCI_TILE_DIM * DPC_TILING_DIM - 10)
                ctx.set_source_rgba(*COLOR_KEY_WALL)
                ctx.fill_preserve()
                ctx.set_source_rgba(*COLOR_OUTLINE)
                ctx.set_line_width(1)
                ctx.stroke()
            # Warp zone
            if action.tr_type == TileRuleType.WARP_ZONE or action.tr_type == TileRuleType.WARP_ZONE_2:
                ctx.rectangle(sx + 5, sy + 5, DPCI_TILE_DIM * DPC_TILING_DIM - 10, DPCI_TILE_DIM * DPC_TILING_DIM - 10)
                ctx.set_source_rgba(*COLOR_WARP_ZONE)
                ctx.fill_preserve()
                ctx.set_source_rgba(*COLOR_OUTLINE)
                ctx.set_line_width(1)
                ctx.stroke()

    def _draw_single_tile(self, ctx, action, x, y):
        type = DmaType.FLOOR
        if isinstance(action, TileRule):
            if action.tr_type.floor_type == FloorType.WALL:
                type = DmaType.WALL
            elif action.tr_type.floor_type == FloorType.SECONDARY:
                type = DmaType.WATER
            elif action.tr_type.floor_type == FloorType.FLOOR_OR_WALL:
                type = DmaType.WALL
        else:
            item, monster, tile, stats = self.entity_rule_container.get(action.entity_rule_id)
            if tile.is_secondary_terrain():
                type = DmaType.WATER

        surf = self.tileset_renderer.get_single_tile(type)
        ctx.translate(x, y)
        ctx.set_source_surface(
            surf, 0, 0
        )
        ctx.get_source().set_filter(cairo.Filter.NEAREST)
        ctx.paint()
        ctx.translate(-x, -y)
