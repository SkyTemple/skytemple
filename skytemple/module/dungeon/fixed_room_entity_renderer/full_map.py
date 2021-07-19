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

import cairo
from gi.repository import GLib

from skytemple.module.dungeon.fixed_room_entity_renderer.abstract import AbstractEntityRenderer
from skytemple_files.dungeon_data.fixed_bin.model import EntityRule, FixedFloorActionRule, TileRuleType, TileRule, \
    DirectRule
from skytemple_files.graphics.dpc.model import DPC_TILING_DIM
from skytemple_files.graphics.dpci.model import DPCI_TILE_DIM
COLOR_ITEM = (0, 0.3, 1, 1)
COLOR_OUTLINE = (0, 0, 0, 1)


class FullMapEntityRenderer(AbstractEntityRenderer):
    def draw_action(self, ctx: cairo.Context, action: FixedFloorActionRule, sx: int, sy: int):
        if isinstance(action, EntityRule):
            item, monster, tile, stats = self.parent.entity_rule_container.get(action.entity_rule_id)
            # Has trap?
            if tile.trap_id < 25:
                sprite, x, y, w, h = self.parent.sprite_provider.get_for_trap(
                    tile.trap_id,
                    lambda: GLib.idle_add(self.parent.redraw)
                )
                ctx.translate(sx, sy)
                ctx.set_source_surface(sprite)
                ctx.paint()
                ctx.get_source().set_filter(cairo.Filter.NEAREST)
                ctx.translate(-sx, -sy)
            # Has item?
            if item.item_id > 0:
                try:
                    itm = self.parent.module.get_item(item.item_id)
                    sprite, x, y, w, h = self.parent.sprite_provider.get_for_item(
                        itm,
                        lambda: GLib.idle_add(self.parent.redraw)
                    )
                    ctx.translate(sx + 4, sy + 4)
                    ctx.set_source_surface(sprite)
                    ctx.get_source().set_filter(cairo.Filter.NEAREST)
                    ctx.paint()
                    ctx.translate(-sx - 4, -sy - 4)
                except IndexError:
                    ctx.arc(sx + DPCI_TILE_DIM * DPC_TILING_DIM / 2, sy + DPCI_TILE_DIM * DPC_TILING_DIM / 2,
                            DPCI_TILE_DIM * DPC_TILING_DIM / 2, 0, 2 * math.pi)
                    ctx.set_source_rgba(*COLOR_ITEM)
                    ctx.fill_preserve()
                    ctx.set_source_rgba(*COLOR_OUTLINE)
                    ctx.set_line_width(1)
                    ctx.stroke()
            # Has Pokémon?
            if monster.md_idx > 0:
                sprite, cx, cy, w, h = self.parent.sprite_provider.get_monster(
                    monster.md_idx,
                    action.direction.ssa_id if action.direction is not None else 0,
                    lambda: GLib.idle_add(self.parent.redraw)
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
        elif isinstance(action, TileRule):
            # Leader spawn tile
            if action.tr_type == TileRuleType.LEADER_SPAWN:
                self.parent.draw_placeholder(0, sx, sy, action.direction, ctx)
            # Attendant1 spawn tile
            if action.tr_type == TileRuleType.ATTENDANT1_SPAWN:
                self.parent.draw_placeholder(10, sx, sy, action.direction, ctx)
            # Attendant2 spawn tile
            if action.tr_type == TileRuleType.ATTENDANT2_SPAWN:
                self.parent.draw_placeholder(11, sx, sy, action.direction, ctx)
            # Attendant3 spawn tile
            if action.tr_type == TileRuleType.ATTENDANT3_SPAWN:
                self.parent.draw_placeholder(15, sx, sy, action.direction, ctx)
            # Key walls
            if action.tr_type == TileRuleType.FL_WA_ROOM_FLAG_0C or action.tr_type == TileRuleType.FL_WA_ROOM_FLAG_0D:
                sprite, x, y, w, h = self.parent.sprite_provider.get_for_trap(
                    31,
                    lambda: GLib.idle_add(self.parent.redraw)
                )
                ctx.translate(sx, sy)
                ctx.set_source_surface(sprite)
                ctx.get_source().set_filter(cairo.Filter.NEAREST)
                ctx.paint()
                ctx.translate(-sx, -sy)
            # Warp zone
            if action.tr_type == TileRuleType.WARP_ZONE or action.tr_type == TileRuleType.WARP_ZONE_2:
                sprite, x, y, w, h = self.parent.sprite_provider.get_for_trap(
                    28,
                    lambda: GLib.idle_add(self.parent.redraw)
                )
                ctx.translate(sx, sy)
                ctx.set_source_surface(sprite)
                ctx.get_source().set_filter(cairo.Filter.NEAREST)
                ctx.paint()
                ctx.translate(-sx, -sy)
        elif isinstance(action, DirectRule):
            pass  # TODO DIRECTRULE
