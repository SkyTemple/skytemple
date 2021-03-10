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
import re
from typing import TYPE_CHECKING

from gi.repository import Gtk
from gi.repository.Gtk import Widget

from skytemple.core.module_controller import AbstractController
from skytemple.core.string_provider import StringType
from skytemple.module.dungeon import MAX_ITEMS, SPECIAL_ITEMS, SPECIAL_MONSTERS
from skytemple_files.data.md.model import NUM_ENTITIES
from skytemple_files.dungeon_data.fixed_bin.model import TileRuleType
from skytemple_files.dungeon_data.mappa_bin.trap_list import MappaTrapType
from skytemple_files.hardcoded.fixed_floor import MonsterSpawnType
from skytemple_files.common.i18n_util import f, _

if TYPE_CHECKING:
    from skytemple.module.dungeon.module import DungeonModule

FIXED_ROOMS_NAME = _('Fixed Rooms')
PATTERN = re.compile(r'.*\([#$](\d+)\).*')


class FixedRoomsController(AbstractController):
    # If set, this entity will be focused on first load
    focus_entity_on_open = None

    def __init__(self, module: 'DungeonModule', item_id: int):
        self.module = module
        self.builder = None
        self.lst_entity, self.lst_item, self.lst_monster, self.lst_tile, self.lst_stats = \
            module.get_fixed_floor_entity_lists()

        self.enemy_settings_name = [f"{i}: ???" for i in range(0, 256)]
        for spawn_type in MonsterSpawnType:
            self.enemy_settings_name[spawn_type.value] = f"{spawn_type.value}: {spawn_type.description}"

        self.monster_names = {}
        length = len(self.module.get_monster_md().entries)
        for i, entry in enumerate(self.module.get_monster_md().entries):
            name = self.module.project.get_string_provider().get_value(StringType.POKEMON_NAMES, i % NUM_ENTITIES)
            self.monster_names[i] = f'{name} ({entry.gender.print_name}) (${i:04})'
        for i in range(length, length + SPECIAL_MONSTERS):
            self.monster_names[i] = _('(Special?)') + f' (${i:04})'

        self.item_names = {}
        for i in range(0, MAX_ITEMS):
            name = self.module.project.get_string_provider().get_value(StringType.ITEM_NAMES, i)
            self.item_names[i] = f'{name} (#{i:04})'
        for i in range(MAX_ITEMS, MAX_ITEMS + SPECIAL_ITEMS):
            self.item_names[i] = _('(Special?)') + f' (#{i:04})'

    def get_view(self) -> Widget:
        self.builder = self._get_builder(__file__, 'fixed_rooms.glade')

        self._fill_entities()
        if self.__class__.focus_entity_on_open:
            t: Gtk.TreeView = self.builder.get_object('tree_entities')
            s: Gtk.TreeSelection = t.get_selection()
            p = t.get_model()[self.__class__.focus_entity_on_open].path
            s.select_path(p)
            t.scroll_to_cell(p, use_align=True, row_align=0.5)
            self.__class__.focus_entity_on_open = None

        self._init_tiles()
        self._init_items()
        self._init_monsters()

        self.builder.connect_signals(self)

        return self.builder.get_object('box_list')

    def on_nb_sl_switch_page(self, n: Gtk.Notebook, p, pnum, *args):
        if pnum == 0:
            self._fill_entities()
        elif pnum == 1:
            self._fill_tiles()
        elif pnum == 2:
            self._fill_items()
        elif pnum == 3:
            self._fill_monsters()
        else:
            self._fill_stats()

    def on_cr_entities_tile_id_changed(self, widget, path, new_iter, *args):
        store: Gtk.Store = self.builder.get_object('model_entities')
        cb_store: Gtk.Store = self.builder.get_object('model_entities__tiles')
        store[path][1] = f'{_("Tile")} {cb_store[new_iter][0]}'
        self.lst_entity[int(store[path][0])].tile_id = cb_store[new_iter][0]
        store[path][4] = self.module.desc_fixed_floor_tile(self.lst_tile[cb_store[new_iter][0]])
        self._save()

    def on_cr_entities_item_id_changed(self, widget, path, new_iter, *args):
        store: Gtk.Store = self.builder.get_object('model_entities')
        cb_store: Gtk.Store = self.builder.get_object('model_entities__items')
        store[path][2] = f'{_("Item")} {cb_store[new_iter][0]}'
        self.lst_entity[int(store[path][0])].item_id = cb_store[new_iter][0]
        store[path][5] = self.module.desc_fixed_floor_item(self.lst_item[cb_store[new_iter][0]].item_id)
        self._save()

    def on_cr_entities_monster_id_changed(self, widget, path, new_iter, *args):
        store: Gtk.Store = self.builder.get_object('model_entities')
        cb_store: Gtk.Store = self.builder.get_object('model_entities__monsters')
        store[path][3] = f'Pokémon {cb_store[new_iter][0]}'
        self.lst_entity[int(store[path][0])].monster_id = cb_store[new_iter][0]
        monster = self.lst_monster[cb_store[new_iter][0]]
        store[path][6] = self.module.desc_fixed_floor_monster(
            monster.md_idx, monster.enemy_settings.value, self.monster_names, self.enemy_settings_name
        )
        self._save()

    def on_btn_entities_goto_monster_clicked(self, *args):
        tree: Gtk.TreeView = self.builder.get_object('tree_entities')
        model, treeiter = tree.get_selection().get_selected()
        if model is not None and treeiter is not None:
            notebook: Gtk.Notebook = self.builder.get_object('nb_sl')
            notebook.set_current_page(3)
            t: Gtk.TreeView = self.builder.get_object('tree_monsters')
            s: Gtk.TreeSelection = t.get_selection()
            p = t.get_model()[self.lst_entity[int(model[treeiter][0])].monster_id].path
            s.select_path(p)
            t.scroll_to_cell(p, use_align=True, row_align=0.5)

    def on_btn_entities_goto_item_clicked(self, *args):
        tree: Gtk.TreeView = self.builder.get_object('tree_entities')
        model, treeiter = tree.get_selection().get_selected()
        if model is not None and treeiter is not None:
            notebook: Gtk.Notebook = self.builder.get_object('nb_sl')
            notebook.set_current_page(2)
            t: Gtk.TreeView = self.builder.get_object('tree_items')
            s: Gtk.TreeSelection = t.get_selection()
            p = t.get_model()[self.lst_entity[int(model[treeiter][0])].item_id].path
            s.select_path(p)
            t.scroll_to_cell(p, use_align=True, row_align=0.5)

    def on_btn_entities_goto_tile_clicked(self, *args):
        tree: Gtk.TreeView = self.builder.get_object('tree_entities')
        model, treeiter = tree.get_selection().get_selected()
        if model is not None and treeiter is not None:
            notebook: Gtk.Notebook = self.builder.get_object('nb_sl')
            notebook.set_current_page(1)
            t: Gtk.TreeView = self.builder.get_object('tree_tiles')
            s: Gtk.TreeSelection = t.get_selection()
            p = t.get_model()[self.lst_entity[int(model[treeiter][0])].tile_id].path
            s.select_path(p)
            t.scroll_to_cell(p, use_align=True, row_align=0.5)

    def on_btn_monsters_goto_stats_clicked(self, *args):
        tree: Gtk.TreeView = self.builder.get_object('tree_monsters')
        model, treeiter = tree.get_selection().get_selected()
        if model is not None and treeiter is not None:
            if not model[treeiter][7]:
                return
            notebook: Gtk.Notebook = self.builder.get_object('nb_sl')
            notebook.set_current_page(4)
            t: Gtk.TreeView = self.builder.get_object('tree_stats')
            s: Gtk.TreeSelection = t.get_selection()
            p = t.get_model()[self.lst_monster[int(model[treeiter][0])].stats_entry].path
            s.select_path(p)
            t.scroll_to_cell(p, use_align=True, row_align=0.5)

    def on_cr_tiles_trap_id_changed(self, widget, path, new_iter, *args):
        store: Gtk.Store = self.builder.get_object('model_tiles')
        cb_store: Gtk.Store = self.builder.get_object('model_tiles__traps')
        store[path][1] = cb_store[new_iter][1]
        self.lst_tile[int(store[path][0])].trap_id = cb_store[new_iter][0]
        self._save()

    def _set_tiles_trap_data_bitflag(self, idx, value, path):
        store: Gtk.Store = self.builder.get_object('model_tiles')
        store[path][idx + 2] = value
        if value:  # TRUE
            self.lst_tile[int(store[path][0])].trap_data |= 1 << idx
        else:  # FALSE
            self.lst_tile[int(store[path][0])].trap_data &= ~(1 << idx)
        self._save()

    def on_cr_tiles_bf1_0_toggled(self, widget, path):
        self._set_tiles_trap_data_bitflag(0, not widget.get_active(), path)

    def on_cr_tiles_bf1_1_toggled(self, widget, path):
        self._set_tiles_trap_data_bitflag(1, not widget.get_active(), path)

    def on_cr_tiles_bf1_2_toggled(self, widget, path):
        self._set_tiles_trap_data_bitflag(2, not widget.get_active(), path)

    def on_cr_tiles_bf1_3_toggled(self, widget, path):
        self._set_tiles_trap_data_bitflag(3, not widget.get_active(), path)

    def on_cr_tiles_bf1_4_toggled(self, widget, path):
        self._set_tiles_trap_data_bitflag(4, not widget.get_active(), path)

    def on_cr_tiles_bf1_5_toggled(self, widget, path):
        self._set_tiles_trap_data_bitflag(5, not widget.get_active(), path)

    def on_cr_tiles_bf1_6_toggled(self, widget, path):
        self._set_tiles_trap_data_bitflag(6, not widget.get_active(), path)

    def on_cr_tiles_bf1_7_toggled(self, widget, path):
        self._set_tiles_trap_data_bitflag(7, not widget.get_active(), path)

    def on_cr_tiles_room_id_edited(self, widget, path, text):
        store: Gtk.Store = self.builder.get_object('model_tiles')
        try:
            v = int(text)
        except:
            return
        store[path][10] = text
        self.lst_tile[int(store[path][0])].room_id = v
        self._save()

    def _set_tiles_flags_data_bitflag(self, idx, value, path):
        store: Gtk.Store = self.builder.get_object('model_tiles')
        store[path][idx + 11] = value
        if value:  # TRUE
            self.lst_tile[int(store[path][0])].flags |= 1 << idx
        else:  # FALSE
            self.lst_tile[int(store[path][0])].flags &= ~(1 << idx)
        self._save()

    def on_cr_tiles_bf2_0_toggled(self, widget, path):
        self._set_tiles_flags_data_bitflag(0, not widget.get_active(), path)

    def on_cr_tiles_bf2_1_toggled(self, widget, path):
        self._set_tiles_flags_data_bitflag(1, not widget.get_active(), path)

    def on_cr_tiles_bf2_2_toggled(self, widget, path):
        self._set_tiles_flags_data_bitflag(2, not widget.get_active(), path)

    def on_cr_tiles_bf2_3_toggled(self, widget, path):
        self._set_tiles_flags_data_bitflag(3, not widget.get_active(), path)

    def on_cr_tiles_bf2_4_toggled(self, widget, path):
        self._set_tiles_flags_data_bitflag(4, not widget.get_active(), path)

    def on_cr_tiles_bf2_5_toggled(self, widget, path):
        self._set_tiles_flags_data_bitflag(5, not widget.get_active(), path)

    def on_cr_tiles_bf2_6_toggled(self, widget, path):
        self._set_tiles_flags_data_bitflag(6, not widget.get_active(), path)

    def on_cr_tiles_bf2_7_toggled(self, widget, path):
        self._set_tiles_flags_data_bitflag(7, not widget.get_active(), path)

    def on_cr_items_item_name_editing_started(self, renderer, editable, path):
        editable.set_completion(self.builder.get_object('completion_items'))

    def on_cr_items_item_name_edited(self, widget, path, text):
        store: Gtk.Store = self.builder.get_object('model_items')
        match = PATTERN.match(text)
        if match is None:
            return
        try:
            idx = int(match.group(1))
        except ValueError:
            return
        store[path][1] = idx
        store[path][2] = self.item_names[idx]
        self.lst_item[int(store[path][0])].item_id = idx
        self._save()

    def on_cr_monsters_monster_editing_started(self, renderer, editable, path):
        editable.set_completion(self.builder.get_object('completion_monsters'))

    def on_cr_monsters_monster_edited(self, widget, path, text):
        store: Gtk.Store = self.builder.get_object('model_monsters')
        match = PATTERN.match(text)
        if match is None:
            return
        try:
            idx = int(match.group(1))
        except ValueError:
            return
        store[path][1] = idx
        store[path][2] = self.monster_names[idx]
        self.lst_monster[int(store[path][0])].md_idx = idx
        self._save()

    def on_cr_monsters_type_changed(self, widget, path, new_iter, *args):
        store: Gtk.Store = self.builder.get_object('model_monsters')
        cb_store: Gtk.Store = self.builder.get_object('model_monsters__type')
        store[path][3] = cb_store[new_iter][0]
        store[path][4] = cb_store[new_iter][1]
        self.lst_monster[int(store[path][0])].enemy_settings = MonsterSpawnType(cb_store[new_iter][0])
        self._save()

    def on_cr_monsters_stats_changed(self, widget, path, new_iter, *args):
        store: Gtk.Store = self.builder.get_object('model_monsters')
        cb_store: Gtk.Store = self.builder.get_object('model_monsters__stats')
        store[path][5] = cb_store[new_iter][0]
        store[path][6] = cb_store[new_iter][1]
        self.lst_monster[int(store[path][0])].stats_entry = cb_store[new_iter][0]
        self._save()

    def on_cr_stats_level_edited(self, widget, path, text):
        store: Gtk.Store = self.builder.get_object('model_stats')
        try:
            v = int(text)
        except:
            return
        store[path][1] = text
        self.lst_stats[int(store[path][0])].level = v
        self._save()

    def on_cr_stats_hp_edited(self, widget, path, text):
        store: Gtk.Store = self.builder.get_object('model_stats')
        try:
            v = int(text)
        except:
            return
        store[path][2] = text
        self.lst_stats[int(store[path][0])].hp = v
        self._save()

    def on_cr_stats_exp_yield_edited(self, widget, path, text):
        store: Gtk.Store = self.builder.get_object('model_stats')
        try:
            v = int(text)
        except:
            return
        store[path][3] = text
        self.lst_stats[int(store[path][0])].exp_yield = v
        self._save()

    def on_cr_stats_atk_edited(self, widget, path, text):
        store: Gtk.Store = self.builder.get_object('model_stats')
        try:
            v = int(text)
        except:
            return
        store[path][4] = text
        self.lst_stats[int(store[path][0])].attack = v
        self._save()

    def on_cr_stats_sp_atk_edited(self, widget, path, text):
        store: Gtk.Store = self.builder.get_object('model_stats')
        try:
            v = int(text)
        except:
            return
        store[path][5] = text
        self.lst_stats[int(store[path][0])].special_attack = v
        self._save()

    def on_cr_stats_def_edited(self, widget, path, text):
        store: Gtk.Store = self.builder.get_object('model_stats')
        try:
            v = int(text)
        except:
            return
        store[path][6] = text
        self.lst_stats[int(store[path][0])].defense = v
        self._save()

    def on_cr_stats_sp_def_edited(self, widget, path, text):
        store: Gtk.Store = self.builder.get_object('model_stats')
        try:
            v = int(text)
        except:
            return
        store[path][7] = text
        self.lst_stats[int(store[path][0])].special_defense = v
        self._save()

    def on_cr_stats_unka_edited(self, widget, path, text):
        store: Gtk.Store = self.builder.get_object('model_stats')
        try:
            v = int(text)
        except:
            return
        store[path][8] = text
        self.lst_stats[int(store[path][0])].unkA = v
        self._save()

    def _fill_entities(self):
        # Init Tiles Store
        store: Gtk.ListStore = self.builder.get_object('model_entities__tiles')
        store.clear()
        for i in range(0, len(self.lst_tile)):
            store.append([i, f"{_('Tile')} {i} ({self.module.desc_fixed_floor_tile(self.lst_tile[i])})"])
        # Init Monsters Store
        store: Gtk.ListStore = self.builder.get_object('model_entities__monsters')
        store.clear()
        for i in range(0, len(self.lst_monster)):
            monster = self.lst_monster[i]
            monster_desc = self.module.desc_fixed_floor_monster(
                monster.md_idx, monster.enemy_settings.value, self.monster_names, self.enemy_settings_name
            )
            store.append([i, f"Pokémon {i} ({monster_desc})"])
        # Init Items Store
        store: Gtk.ListStore = self.builder.get_object('model_entities__items')
        store.clear()
        for i in range(0, len(self.lst_item)):
            store.append([i, f"{_('Item')} {i} ({self.module.desc_fixed_floor_item(self.lst_item[i].item_id)})"])

        # Init Entities Store
        store: Gtk.ListStore = self.builder.get_object('model_entities')
        store.clear()
        reserved_ids = [x.value for x in TileRuleType]
        for idx, entity in enumerate(self.lst_entity):
            # Remove ids that don't actually represent entities
            if idx + 16 in reserved_ids:
                continue;
            monster = self.lst_monster[entity.monster_id]
            store.append([
                str(idx), f"{_('Tile')} {entity.tile_id}", f"{_('Item')} {entity.item_id}", f"Pokémon {entity.monster_id}",
                "(" + self.module.desc_fixed_floor_tile(self.lst_tile[entity.tile_id]) + ")",
                "(" + self.module.desc_fixed_floor_item(self.lst_item[entity.item_id].item_id) + ")",
                "(" + self.module.desc_fixed_floor_monster(
                    monster.md_idx, monster.enemy_settings.value, self.monster_names, self.enemy_settings_name
                ) + ")"
            ])

    def _init_tiles(self):
        # Init Traps Store
        store: Gtk.ListStore = self.builder.get_object('model_tiles__traps')
        store.append([25, _('None')])
        for trap in MappaTrapType:
            store.append([trap.value, trap.print_name])

    def _fill_tiles(self):
        # Init Tiles Store
        store: Gtk.ListStore = self.builder.get_object('model_tiles')
        store.clear()
        for idx, tile in enumerate(self.lst_tile):
            name = _('None')
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

        for item in self.item_names.values():
            store.append([item])

    def _fill_items(self):
        # Init Items Store
        store: Gtk.ListStore = self.builder.get_object('model_items')
        store.clear()
        for idx, item in enumerate(self.lst_item):
            store.append([
                str(idx), item.item_id, self.item_names[item.item_id]
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

    def _fill_monsters(self):
        # Init Monsters Stats
        store: Gtk.ListStore = self.builder.get_object('model_monsters__stats')
        store.clear()
        for i, entry in enumerate(self.lst_stats):
            store.append([i, self._generate_stats_label(i, entry)])

        # Init Monsters Store
        store: Gtk.ListStore = self.builder.get_object('model_monsters')
        store.clear()
        for idx, monster in enumerate(self.lst_monster):
            store.append([
                str(idx), monster.md_idx, self.monster_names[monster.md_idx], monster.enemy_settings.value,
                self.enemy_settings_name[monster.enemy_settings.value], *self._generate_stats_store_entry(monster)
            ])

    def _fill_stats(self):
        # Init Stats Store
        store: Gtk.ListStore = self.builder.get_object('model_stats')
        store.clear()
        for idx, item in enumerate(self.lst_stats):
            store.append([
                str(idx), str(item.level), str(item.hp), str(item.exp_yield),
                str(item.attack), str(item.special_attack), str(item.defense), str(item.special_defense),
                str(item.unkA)
            ])

    def _generate_stats_store_entry(self, monster):
        if monster.enemy_settings == MonsterSpawnType.ENEMY_STRONG or monster.enemy_settings == MonsterSpawnType.ALLY_HELP:
            return (monster.stats_entry,
                    self._generate_stats_label(monster.stats_entry, self.lst_stats[monster.stats_entry]),
                    True)
        return 0, _('n/a'), False

    def _generate_stats_label(self, i, entry):
        return self.module.desc_fixed_floor_stats(i, entry)

    def _save(self):
        self.module.save_fixed_floor_entity_lists(self.lst_entity, self.lst_item,
                                                  self.lst_monster, self.lst_tile, self.lst_stats)
