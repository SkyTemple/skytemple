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
import cairo

from skytemple.module.dungeon.fixed_room_entity_renderer.abstract import AbstractEntityRenderer
from skytemple.module.dungeon.minimap_provider import MinimapProvider, ZMAPPAT_DIM
from skytemple_files.common.dungeon_floor_generator.generator import TileType, RoomType
from skytemple_files.dungeon_data.fixed_bin.model import EntityRule, FixedFloorActionRule, TileRuleType, TileRule, \
    DirectRule
from skytemple_files.dungeon_data.mappa_bin.protocol import MappaTrapType
from skytemple_files.hardcoded.fixed_floor import MonsterSpawnType

COLOR_ITEM = (0, 0.3, 1, 1)
COLOR_OUTLINE = (0, 0, 0, 1)


class MinimapEntityRenderer(AbstractEntityRenderer):
    def __init__(self, parent, minimap_provider: MinimapProvider):
        super().__init__(parent)
        self.minimap_provider = minimap_provider

    def draw_action(self, ctx: cairo.Context, action: FixedFloorActionRule, x: int, y: int):
        if isinstance(action, EntityRule):
            assert self.parent.entity_rule_container is not None
            item, monster, tile, stats = self.parent.entity_rule_container.get(action.entity_rule_id)
            # Has trap?
            if tile.trap_id == MappaTrapType.WONDER_TILE.value:
                self.paint(ctx, self.minimap_provider.get_minimap_tile(7), x, y)
            elif tile.trap_id < 25:
                self.paint(ctx, self.minimap_provider.get_minimap_tile(4), x, y)
            # Has item?
            if item.item_id > 0:
                self.paint(ctx, self.minimap_provider.get_minimap_tile(3), x, y)
            # Has Pokémon?
            if monster.md_idx > 0:
                if monster.enemy_settings == MonsterSpawnType.ENEMY_STRONG or \
                        monster.enemy_settings == MonsterSpawnType.ENEMY_NORMAL or \
                        monster.enemy_settings == MonsterSpawnType.ENEMY_OUTLAW or \
                        monster.enemy_settings == MonsterSpawnType.ENEMY_NORMAL_2 or \
                        monster.enemy_settings == MonsterSpawnType.OUTLAW or \
                        monster.enemy_settings == MonsterSpawnType.OUTLAW_RUN or \
                        monster.enemy_settings == MonsterSpawnType.UNKNOWN_F:
                    self.paint(ctx, self.minimap_provider.get_minimap_tile(2), x, y)
                else:
                    self.paint(ctx, self.minimap_provider.get_minimap_tile(10), x, y)
        elif isinstance(action, TileRule):
            # Leader spawn tile
            if action.tr_type == TileRuleType.LEADER_SPAWN:
                self.paint(ctx, self.minimap_provider.get_minimap_tile(8), x, y)
            # Attendant1 spawn tile
            if action.tr_type == TileRuleType.ATTENDANT1_SPAWN:
                self.paint(ctx, self.minimap_provider.get_minimap_tile(10), x, y)
            # Attendant2 spawn tile
            if action.tr_type == TileRuleType.ATTENDANT2_SPAWN:
                self.paint(ctx, self.minimap_provider.get_minimap_tile(10), x, y)
            # Attendant3 spawn tile
            if action.tr_type == TileRuleType.ATTENDANT3_SPAWN:
                self.paint(ctx, self.minimap_provider.get_minimap_tile(10), x, y)
            # Key walls
            if action.tr_type == TileRuleType.FL_WA_ROOM_FLAG_0C or action.tr_type == TileRuleType.FL_WA_ROOM_FLAG_0D:
                self.paint(ctx, self.minimap_provider.get_minimap_tile(9), x, y)
            # Warp zone
            if action.tr_type == TileRuleType.WARP_ZONE or action.tr_type == TileRuleType.WARP_ZONE_2:
                self.paint(ctx, self.minimap_provider.get_minimap_tile(5), x, y)
        elif isinstance(action, DirectRule):
            if action.tile.typ == TileType.PLAYER_SPAWN:
                self.paint(ctx, self.minimap_provider.get_minimap_tile(8), x, y)
            if action.tile.typ == TileType.ENEMY:
                self.paint(ctx, self.minimap_provider.get_minimap_tile(2), x, y)
            if action.tile.typ == TileType.STAIRS:
                self.paint(ctx, self.minimap_provider.get_minimap_tile(6), x, y)
            if action.tile.typ == TileType.TRAP:
                if action.itmtpmon_id == MappaTrapType.WONDER_TILE.value:
                    self.paint(ctx, self.minimap_provider.get_minimap_tile(7), x, y)
                else:
                    self.paint(ctx, self.minimap_provider.get_minimap_tile(4), x, y)
            if action.tile.typ == TileType.BURIED_ITEM:
                self.paint(ctx, self.minimap_provider.get_buried_item_tile(), x, y)
            if action.tile.typ == TileType.ITEM:
                self.paint(ctx, self.minimap_provider.get_minimap_tile(3), x, y)
            if action.tile.room_type == RoomType.KECLEON_SHOP:
                ctx.set_source_rgba(230, 230, 0, 0.2)
                ctx.rectangle(x, y, ZMAPPAT_DIM, ZMAPPAT_DIM)
                ctx.fill()
            if action.tile.room_type == RoomType.MONSTER_HOUSE:
                ctx.set_source_rgba(230, 0, 0, 0.2)
                ctx.rectangle(x, y, ZMAPPAT_DIM, ZMAPPAT_DIM)
                ctx.fill()

    def paint(self, ctx, source, x, y):
        ctx.translate(x, y)
        ctx.set_source_surface(source)
        ctx.get_source().set_filter(cairo.Filter.NEAREST)
        ctx.paint()
        ctx.translate(-x, -y)
