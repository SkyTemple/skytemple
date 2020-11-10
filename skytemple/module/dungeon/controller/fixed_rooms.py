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
from typing import TYPE_CHECKING

from gi.repository import Gtk
from gi.repository.Gtk import Widget

from skytemple.core.module_controller import AbstractController
from skytemple.core.string_provider import StringType
from skytemple.module.dungeon import MAX_ITEM_ID, SPECIAL_ITEMS, SPECIAL_MONSTERS
from skytemple_files.data.md.model import NUM_ENTITIES
from skytemple_files.dungeon_data.mappa_bin.trap_list import MappaTrapType

if TYPE_CHECKING:
    from skytemple.module.dungeon.module import DungeonModule

FIXED_ROOMS_NAME = 'Fixed Rooms'


class FixedRoomsController(AbstractController):
    def __init__(self, module: 'DungeonModule', item_id: int):
        self.module = module
        self.builder = None
        self.lst_entity, self.lst_item, self.lst_monster, self.lst_tile, self.lst_stats = \
            module.get_fixed_floor_entity_lists()

        self.enemy_settings_name = [f"{i}: ???" for i in range(0, 256)]
        self.enemy_settings_name[6] = "6: Enemy"
        self.enemy_settings_name[9] = "9: Ally"
        self.enemy_settings_name[10] = "10: Invalid?"

        self.monster_names = {}
        length = len(self.module.get_monster_md().entries)
        for i, entry in enumerate(self.module.get_monster_md().entries):
            name = self.module.project.get_string_provider().get_value(StringType.POKEMON_NAMES, i % NUM_ENTITIES)
            self.monster_names[i] = f'{name} ({entry.gender.name.capitalize()}) (${i:04})'
        for i in range(length, length + SPECIAL_MONSTERS):
            self.monster_names[i] = f'(Special?) (${i:04})'

    def get_view(self) -> Widget:
        self.builder = self._get_builder(__file__, 'fixed_rooms.glade')

        self._init_entities()
        self._init_tiles()
        self._init_items()
        self._init_monsters()

        self.builder.connect_signals(self)

        return self.builder.get_object('box_list')

    def on_cr_entities_tile_id_changed(self, *args):
        pass  # todo

    def on_cr_entities_item_id_changed(self, *args):
        pass  # todo

    def on_cr_entities_monster_id_changed(self, *args):
        pass  # todo

    def on_cr_tiles_trap_id_changed(self, *args):
        pass  # todo

    def on_cr_tiles_bf1_0_toggled(self, *args):
        pass  # todo

    def on_cr_tiles_bf1_1_toggled(self, *args):
        pass  # todo

    def on_cr_tiles_bf1_2_toggled(self, *args):
        pass  # todo

    def on_cr_tiles_bf1_3_toggled(self, *args):
        pass  # todo

    def on_cr_tiles_bf1_4_toggled(self, *args):
        pass  # todo

    def on_cr_tiles_bf1_5_toggled(self, *args):
        pass  # todo

    def on_cr_tiles_bf1_6_toggled(self, *args):
        pass  # todo

    def on_cr_tiles_bf1_7_toggled(self, *args):
        pass  # todo

    def on_cr_tiles_room_id_edited(self, *args):
        pass  # todo

    def on_cr_tiles_bf2_0_toggled(self, *args):
        pass  # todo

    def on_cr_tiles_bf2_1_toggled(self, *args):
        pass  # todo

    def on_cr_tiles_bf2_2_toggled(self, *args):
        pass  # todo

    def on_cr_tiles_bf2_3_toggled(self, *args):
        pass  # todo

    def on_cr_tiles_bf2_4_toggled(self, *args):
        pass  # todo

    def on_cr_tiles_bf2_5_toggled(self, *args):
        pass  # todo

    def on_cr_tiles_bf2_6_toggled(self, *args):
        pass  # todo

    def on_cr_tiles_bf2_7_toggled(self, *args):
        pass  # todo

    def on_cr_items_item_name_edited(self, *args):
        pass  # todo

    def on_cr_monsters_monster_edited(self, *args):
        pass  # todo

    def on_cr_monsters_type_changed(self, *args):
        pass  # todo

    def _init_entities(self):
        # Init Tiles Store
        store: Gtk.ListStore = self.builder.get_object('model_entities__tiles')
        for i in range(0, len(self.lst_tile)):
            store.append([i, f"Tile {i}"])
        # Init Monsters Store
        store: Gtk.ListStore = self.builder.get_object('model_entities__monsters')
        for i in range(0, len(self.lst_monster)):
            store.append([i, f"Pokémon {i}"])
        # Init Items Store
        store: Gtk.ListStore = self.builder.get_object('model_entities__items')
        for i in range(0, len(self.lst_item)):
            store.append([i, f"Item {i}"])
        # Init Entities Store
        store: Gtk.ListStore = self.builder.get_object('model_entities')
        for idx, entity in enumerate(self.lst_entity):
            store.append([
                str(idx), f"Tile {entity.tile_id}", f"Item {entity.item_id}", f"Pokémon {entity.monster_id}",
                self._desc_tile(entity.tile_id), self._desc_item(entity.item_id), self._desc_monster(entity.monster_id)
            ])

    def _init_tiles(self):
        # Init Traps Store
        store: Gtk.ListStore = self.builder.get_object('model_tiles__traps')
        store.append([25, 'None'])
        for trap in MappaTrapType:
            store.append([trap.value, ' '.join([x.capitalize() for x in trap.name.split('_')])])
        # Init Tiles Store
        store: Gtk.ListStore = self.builder.get_object('model_tiles')
        for idx, tile in enumerate(self.lst_tile):
            name = 'None'
            if tile.trap_id < 25:
                trap = MappaTrapType(tile.trap_id)
                name = ' '.join([x.capitalize() for x in trap.name.split('_')])
            store.append([
                str(idx), name,
                *(bool(tile.trap_data >> i & 1) for i in range(8)), str(tile.room_id),
                *(bool(tile.flags >> i & 1) for i in range(8))
            ])

    def _init_items(self):
        # Init Items Completion
        store: Gtk.ListStore = self.builder.get_object('store_completion_items')

        item_names = {}
        for i in range(0, MAX_ITEM_ID):
            name = self.module.project.get_string_provider().get_value(StringType.ITEM_NAMES, i)
            item_names[i] = f'{name} (#{i:04})'
        for i in range(MAX_ITEM_ID, MAX_ITEM_ID + SPECIAL_ITEMS):
            item_names[i] = f'(Special?) (#{i:04})'
        for item in item_names.values():
            store.append([item])

        # Init Items Store
        store: Gtk.ListStore = self.builder.get_object('model_items')
        for idx, item in enumerate(self.lst_item):
            store.append([
                str(idx), item.item_id, item_names[item.item_id]
            ])

    def _init_monsters(self):
        # Init Monsters Completion
        store: Gtk.ListStore = self.builder.get_object('store_completion_monsters')

        for item in self.monster_names.values():
            store.append([item])

        # Init Monsters Types
        store: Gtk.ListStore = self.builder.get_object('model_monsters__type')
        for i, entry in enumerate(self.enemy_settings_name):
            store.append([i, entry])

        # Init Monsters Store
        store: Gtk.ListStore = self.builder.get_object('model_monsters')
        for idx, monster in enumerate(self.lst_monster):
            store.append([
                str(idx), monster.md_idx, self.monster_names[monster.md_idx], monster.enemy_settings,
                self.enemy_settings_name[monster.enemy_settings]
            ])

    def _desc_tile(self, tile_id):
        tile = self.lst_tile[tile_id]
        attrs = []
        attrs.append("Floor" if not tile.is_secondary_terrain() else "Secondary")
        if tile.trap_id < 25:
            trap = MappaTrapType(tile.trap_id)
            attrs.append(' '.join([x.capitalize() for x in trap.name.split('_')]))
        if tile.trap_is_visible():
            attrs.append("Vis.")
        if not tile.can_be_broken():
            attrs.append("Unb.")
        return ", ".join(attrs)

    def _desc_item(self, item_id):
        item_id = self.lst_item[item_id].item_id
        return self.module.project.get_string_provider().get_value(
            StringType.ITEM_NAMES, item_id
        ) if item_id < MAX_ITEM_ID else "(Special?)"

    def _desc_monster(self, monster_id):
        if monster_id == 0:
            return "Nothing"
        monster = self.lst_monster[monster_id]
        monster_id = monster.md_idx
        return self.monster_names[monster_id] + " (" + self.enemy_settings_name[monster.enemy_settings] + ")"
