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
from typing import List, Optional, Tuple, Generator

from skytemple_files.hardcoded.fixed_floor import EntitySpawnEntry, ItemSpawn, MonsterSpawn, TileSpawn, \
    MonsterSpawnStats


class EntityRuleContainer:
    def __init__(self, entities: List[EntitySpawnEntry], items: List[ItemSpawn], monsters: List[MonsterSpawn],
                 tiles: List[TileSpawn], stats: List[MonsterSpawnStats]):
        self.entities = entities
        self.items = items
        self.monsters = monsters
        self.tiles = tiles
        self.stats = stats

    def get(self, idx: int) -> Tuple[ItemSpawn, MonsterSpawn, TileSpawn, MonsterSpawnStats]:
        entity = self.entities[idx]
        return (
            self.items[entity.item_id],
            self.monsters[entity.monster_id],
            self.tiles[entity.tile_id],
            self.stats[self.monsters[entity.monster_id].stats_entry]
        )

    def __len__(self):
        return len(self.entities)

    def __iter__(self) -> Generator[Tuple[ItemSpawn, MonsterSpawn, TileSpawn, MonsterSpawnStats], None, None]:
        for i in range(0, len(self)):
            yield self.get(i)
