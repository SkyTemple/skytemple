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
import re
from enum import Enum
from functools import partial, reduce
from itertools import zip_longest
from math import gcd
from typing import TYPE_CHECKING, List, Type, Dict

from gi.repository import Gtk, GLib, GdkPixbuf

from skytemple.controller.main import MainController
from skytemple.core.error_handler import display_error
from skytemple.core.module_controller import AbstractController
from skytemple.core.string_provider import StringType
from skytemple_files.common.ppmdu_config.dungeon_data import Pmd2DungeonItem
from skytemple_files.common.util import lcm
from skytemple_files.dungeon_data.mappa_bin.floor_layout import MappaFloorStructureType, MappaFloorSecondaryTerrainType, \
    MappaFloorDarknessLevel, MappaFloorWeather
from skytemple_files.dungeon_data.mappa_bin.item_list import MappaItemList, Probability, GUARANTEED, MappaItemCategory, \
    MAX_ITEM_ID
from skytemple_files.dungeon_data.mappa_bin.monster import DUMMY_MD_INDEX, MappaMonster
from skytemple_files.dungeon_data.mappa_bin.trap_list import MappaTrapType, MappaTrapList

if TYPE_CHECKING:
    from skytemple.module.dungeon.module import DungeonModule, FloorViewInfo


COUNT_VALID_TILESETS = 199
COUNT_VALID_BGM = 117
COUNT_VALID_FIXED_FLOORS = 256
KECLEON_MD_INDEX = 383
CB = 'cb_'
CB_TERRAIN_SETTINGS = 'cb_terrain_settings__'
ENTRY = 'entry_'
ENTRY_TERRAIN_SETTINGS = 'entry_terrain_settings__'
SCALE = 'scale_'
PATTERN_MD_ENTRY = re.compile(r'.*\(#(\d+)\).*')
CSS_HEADER_COLOR = 'dungeon_editor_column_header_invalid'
VALID_ITEM_CATEGORY_NAMES = {
    MappaItemCategory.THROWN_PIERCE: 'Thrown - Pierce',
    MappaItemCategory.THROWN_ROCK: 'Thrown - Rock',
    MappaItemCategory.BERRIES_SEEDS_VITAMINS: 'Berries, Seeds, Vitamins',
    MappaItemCategory.FOODS_GUMMIES: 'Foods, Gummies',
    MappaItemCategory.HOLD: 'Hold',
    MappaItemCategory.TMS: 'TMs, HMs',
    MappaItemCategory.POKE: 'Poké (Money)',
    MappaItemCategory.OTHER: 'Other',
    MappaItemCategory.ORBS: 'Orbs',
    MappaItemCategory.LINK_BOX: 'Link Box'
}
CATEGORIES_FOR_STORES = {
    'item_cat_thrown_pierce_store': MappaItemCategory.THROWN_PIERCE,
    'item_cat_thrown_rock_store': MappaItemCategory.THROWN_ROCK,
    'item_cat_berries_store': MappaItemCategory.BERRIES_SEEDS_VITAMINS,
    'item_cat_foods_store': MappaItemCategory.FOODS_GUMMIES,
    'item_cat_hold_store': MappaItemCategory.HOLD,
    'item_cat_tms_store': MappaItemCategory.TMS,
    'item_cat_orbs_store': MappaItemCategory.ORBS,
    'item_cat_others_store': MappaItemCategory.OTHER
}


class FloorEditItemList(Enum):
    FLOOR = 0
    SHOP = 1
    MONSTER_HOUSE = 2
    BURIED = 3
    UNK1 = 4
    UNK2 = 5


class FloorController(AbstractController):
    _last_open_tab_id = 0
    _last_open_tab_item_lists = FloorEditItemList.FLOOR

    def __init__(self, module: 'DungeonModule', item: 'FloorViewInfo'):
        self.module = module
        self.item = item
        self.entry = self.module.get_mappa_floor(item)

        self.builder = None
        self._refresh_timer = None
        self._loading = False
        self._string_provider = module.project.get_string_provider()
        self._sprite_provider = module.project.get_sprite_provider()

        self._item_list_edit_active = self.__class__._last_open_tab_item_lists

        self._ent_names = {}
        self._item_names = {}

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'floor.glade')

        self._loading = True
        self._init_labels()
        self._init_layout_stores()

        self._init_monster_spawns()
        self._recalculate_spawn_chances('monster_spawns_store', 5, 4)

        self._init_trap_spawns()
        self._recalculate_spawn_chances('trap_spawns_store', 3, 2)

        self._init_item_spawns()
        self._recalculate_spawn_chances('item_categories_store', 4, 3)
        self._recalculate_spawn_chances('item_cat_thrown_pierce_store', 4, 3)
        self._recalculate_spawn_chances('item_cat_thrown_rock_store', 4, 3)
        self._recalculate_spawn_chances('item_cat_berries_store', 4, 3)
        self._recalculate_spawn_chances('item_cat_foods_store', 4, 3)
        self._recalculate_spawn_chances('item_cat_hold_store', 4, 3)
        self._recalculate_spawn_chances('item_cat_tms_store', 4, 3)
        self._recalculate_spawn_chances('item_cat_orbs_store', 4, 3)
        self._recalculate_spawn_chances('item_cat_others_store', 4, 3)

        self._init_layout_values()
        self._loading = False

        self.builder.connect_signals(self)
        # TODO: Dungeon mini preview

        notebook: Gtk.Notebook = self.builder.get_object('floor_notebook')
        notebook.set_current_page(self.__class__._last_open_tab_id)

        item_list_notebook: Gtk.Notebook = self.builder.get_object('item_list_notebook')
        item_list_notebook.set_current_page(self._item_list_edit_active.value)

        self.builder.get_object('layout_grid').check_resize()
        return self.builder.get_object('box_editor')

    # <editor-fold desc="HANDLERS LAYOUT" defaultstate="collapsed">

    def on_floor_notebook_switch_page(self, notebook, page, page_num):
        self.__class__._last_open_tab_id = page_num

    def on_btn_preview_clicked(self, *args):
        pass  # todo

    def on_cb_tileset_id_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_cb_music_id_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_cb_fixed_floor_id_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_btn_export_clicked(self, *args):
        pass  # todo

    def on_btn_import_clicked(self, *args):
        pass  # todo

    def on_entry_room_density_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_btn_help_room_density_clicked(self, *args):
        pass  # todo

    def on_cb_structure_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_cb_dead_ends_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_btn_help_dead_ends_clicked(self, *args):
        pass  # todo

    def on_entry_floor_connectivity_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_entry_water_density_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_btn_help_floor_connectivity_clicked(self, *args):
        pass  # todo

    def on_btn_help_extra_hallway_density_clicked(self, *args):
        pass  # todo

    def on_cb_terrain_settings__has_secondary_terrain_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_cb_secondary_terrain_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_cb_terrain_settings__generate_imperfect_rooms_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_cb_darkness_level_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_cb_weather_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_entry_item_density_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_entry_trap_density_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_entry_initial_enemy_density_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_entry_buried_item_density_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_entry_max_coin_amount_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_btn_help_item_density_clicked(self, *args):
        pass  # todo

    def on_btn_help_trap_density_clicked(self, *args):
        pass  # todo

    def on_btn_help_initial_enemy_density_clicked(self, *args):
        pass  # todo

    def on_btn_help_buried_item_density_clicked(self, *args):
        pass  # todo

    def on_btn_help_max_coin_amount_clicked(self, *args):
        pass  # todo

    def on_btn_help_chances_clicked(self, *args):
        pass  # todo

    def on_btn_help_kecleon_shop_item_positions_clicked(self, *args):
        pass  # todo

    def on_btn_help_unk_hidden_stairs_clicked(self, *args):
        pass  # todo

    def on_scale_kecleon_shop_chance_value_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_scale_monster_house_chance_value_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_scale_unusued_chance_value_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_scale_hidden_stairs_spawn_chance_value_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_entry_kecleon_shop_item_positions_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_scale_empty_monster_house_chance_value_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_btn_help_empty_monster_house_clicked(self, *args):
        pass  # todo

    def on_scale_sticky_item_chance_value_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_entry_unk_hidden_stairs_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_cb_iq_booster_enabled_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_btn_help_iq_booster_enabled_clicked(self, *args):
        pass  # todo

    def on_btn_help_enemy_iq_clicked(self, *args):
        pass  # todo

    def on_entry_enemy_iq_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_cb_unk_e_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_btn_goto_tileset_clicked(self, *args):
        pass

    def on_btn_goto_fixed_floor_clicked(self, *args):
        pass

    # </editor-fold>

    # <editor-fold desc="HANDLERS MONSTERS" defaultstate="collapsed">

    def on_cr_monster_spawns_entity_edited(self, widget, path, text):
        store: Gtk.Store = self.builder.get_object('monster_spawns_store')
        match = PATTERN_MD_ENTRY.match(text)
        if match is None:
            return
        try:
            entid = int(match.group(1))
        except ValueError:
            return

        if entid == KECLEON_MD_INDEX or entid >= DUMMY_MD_INDEX:
            display_error(
                None,
                f"You can not spawn Kecleons or the Decoy Pokémon or any Pokémon above #{DUMMY_MD_INDEX}.",
                "SkyTemple: Invalid Pokémon"
            )
            return

        store[path][0] = entid
        # ent_icon:
        # If color is orange it's special.
        store[path][1] = self._get_icon(entid, path)
        # ent_name:
        store[path][2] = self._ent_names[entid]
        self._save_monster_spawn_rates()

    def on_cr_monster_spawns_entity_editing_started(self, renderer, editable, path):
        editable.set_completion(self.builder.get_object('completion_monsters'))

    def on_cr_monster_spawns_weight_edited(self, widget, path, text):
        try:
            v = int(text)
            assert v >= 0
        except:
            return
        store: Gtk.Store = self.builder.get_object('monster_spawns_store')
        store[path][5] = text

        self._recalculate_spawn_chances('monster_spawns_store', 5, 4)
        self._save_monster_spawn_rates()

    def on_cr_monster_spawns_level_edited(self, widget, path, text):
        try:
            int(text)
        except:
            return
        store: Gtk.Store = self.builder.get_object('monster_spawns_store')
        store[path][3] = text
        self._save_monster_spawn_rates()

    def on_monster_spawns_add_clicked(self, *args):
        store: Gtk.ListStore = self.builder.get_object('monster_spawns_store')
        store.append([
            1, self._get_icon(1, len(store)), self._ent_names[1],
            "1", "0%", "0"
        ])
        self._save_monster_spawn_rates()

    def on_monster_spawns_remove_clicked(self, *args):
        tree: Gtk.TreeView = self.builder.get_object('monster_spawns_tree')
        model, treeiter = tree.get_selection().get_selected()
        if model is not None and treeiter is not None:
            model.remove(treeiter)
        self._recalculate_spawn_chances('monster_spawns_store', 5, 4)
        self._save_monster_spawn_rates()

    def on_kecleon_level_entry_changed(self, w: Gtk.Entry, *args):
        try:
            level = int(w.get_text())
        except:
            return
        for i, monster in enumerate(self.entry.monsters):
            if monster.md_index == KECLEON_MD_INDEX:
                monster.level = level
                break
        self.mark_as_modified()

    # </editor-fold>

    # <editor-fold desc="HANDLERS TRAPS" defaultstate="collapsed">

    def on_cr_trap_spawns_weight_edited(self, widget, path, text):
        try:
            v = int(text)
            assert v >= 0
        except:
            return
        store: Gtk.Store = self.builder.get_object('trap_spawns_store')
        store[path][3] = text

        self._recalculate_spawn_chances('trap_spawns_store', 3, 2)
        self._save_trap_spawn_rates()

    # </editor-fold>

    # <editor-fold desc="ITEM HANDLERS" defaultstate="collapsed">

    def on_cr_items_cat_weight_edited(self, widget, path, text):
        try:
            v = int(text)
            assert v >= 0
        except:
            return
        store: Gtk.Store = self.builder.get_object('item_categories_store')
        store[path][4] = text

        self._recalculate_spawn_chances('item_categories_store', 4, 3)
        self._save_item_spawn_rates()

    def on_item_categories_add_clicked(self, *args):
        store: Gtk.Store = self.builder.get_object('item_categories_store')
        dialog: Gtk.Dialog = self.builder.get_object('dialog_category_add')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        # Init available categories
        available_categories = [
            cat for cat in VALID_ITEM_CATEGORY_NAMES.keys()
            if cat not in self.get_current_item_list().categories.keys()
        ]
        # Show error if no categories available
        if len(available_categories) < 1:
            display_error(
                None,
                'All categories are already in the list.',
                'Can not add category'
            )
            return
        # Init combobox
        cb: Gtk.ComboBoxText = self.builder.get_object('category_add_cb')
        cb_store: Gtk.ListStore = self.builder.get_object('category_add_store')
        cb_store.clear()
        for cat in available_categories:
            cb_store.append([cat.value, VALID_ITEM_CATEGORY_NAMES[cat]])
        cb.set_active_iter(cb_store.get_iter_first())

        resp = dialog.run()
        dialog.hide()
        if resp == Gtk.ResponseType.APPLY:
            row = cb_store[cb.get_active_iter()]
            store.append([
                row[0], row[1],
                False, "0%", "0"
            ])
            self._save_item_spawn_rates()

    def on_item_categories_remove_clicked(self, *args):
        tree: Gtk.TreeView = self.builder.get_object('item_categories_tree')
        model, treeiter = tree.get_selection().get_selected()
        if len(model) < 2:
            display_error(
                None,
                "The last category can not be removed.",
                "Can't remove category."
            )
            return
        if model is not None and treeiter is not None:
            model.remove(treeiter)
        self._recalculate_spawn_chances('item_categories_store', 4, 3)
        self._save_item_spawn_rates()

    def on_cr_items_cat_thrown_pierce_item_name_edited(self, widget, path, text):
        self._on_cat_item_name_changed('item_cat_thrown_pierce_store', path, text)

    def on_cr_items_cat_thrown_pierce_item_name_editing_started(self, renderer, editable, path):
        editable.set_completion(self.builder.get_object('completion_item_thrown_pierce'))

    def on_cr_items_cat_thrown_pierce_guaranteed_toggled(self, widget, path):
        self._on_cat_item_guaranteed_toggled('item_cat_thrown_pierce_store', path, widget.get_active())

    def on_cr_items_cat_thrown_pierce_weight_edited(self, widget, path, text):
        self._on_cat_item_weight_changed('item_cat_thrown_pierce_store', path, text)

    def on_item_cat_thrown_pierce_add_clicked(self, *args):
        self._on_cat_item_add_clicked('item_cat_thrown_pierce_store')

    def on_item_cat_thrown_pierce_remove_clicked(self, *args):
        self._on_cat_item_remove_clicked('item_cat_thrown_pierce_tree')

    def on_cr_items_cat_thrown_rock_item_name_edited(self, widget, path, text):
        self._on_cat_item_name_changed('item_cat_thrown_rock_store', path, text)

    def on_cr_items_cat_thrown_rock_item_name_editing_started(self, renderer, editable, path):
        editable.set_completion(self.builder.get_object('completion_item_thrown_rock'))

    def on_cr_items_cat_thrown_rock_guaranteed_toggled(self, widget, path):
        self._on_cat_item_guaranteed_toggled('item_cat_thrown_rock_store', path, widget.get_active())

    def on_cr_items_cat_thrown_rock_weight_edited(self, widget, path, text):
        self._on_cat_item_weight_changed('item_cat_thrown_rock_store', path, text)

    def on_item_cat_thrown_rock_add_clicked(self, *args):
        self._on_cat_item_add_clicked('item_cat_thrown_rock_store')

    def on_item_cat_thrown_rock_remove_clicked(self, *args):
        self._on_cat_item_remove_clicked('item_cat_thrown_rock_tree')

    def on_cr_items_cat_berries_item_name_edited(self, widget, path, text):
        self._on_cat_item_name_changed('item_cat_berries_store', path, text)

    def on_cr_items_cat_berries_item_name_editing_started(self, renderer, editable, path):
        editable.set_completion(self.builder.get_object('completion_item_berries'))

    def on_cr_items_cat_berries_guaranteed_toggled(self, widget, path):
        self._on_cat_item_guaranteed_toggled('item_cat_berries_store', path, widget.get_active())

    def on_cr_items_cat_berries_weight_edited(self, widget, path, text):
        self._on_cat_item_weight_changed('item_cat_berries_store', path, text)

    def on_item_cat_berries_add_clicked(self, *args):
        self._on_cat_item_add_clicked('item_cat_berries_store')

    def on_item_cat_berries_remove_clicked(self, *args):
        self._on_cat_item_remove_clicked('item_cat_berries_tree')

    def on_cr_items_cat_foods_item_name_edited(self, widget, path, text):
        self._on_cat_item_name_changed('item_cat_foods_store', path, text)

    def on_cr_items_cat_foods_item_name_editing_started(self, renderer, editable, path):
        editable.set_completion(self.builder.get_object('completion_item_foods'))

    def on_cr_items_cat_foods_guaranteed_toggled(self, widget, path):
        self._on_cat_item_guaranteed_toggled('item_cat_foods_store', path, widget.get_active())

    def on_cr_items_cat_foods_weight_edited(self, widget, path, text):
        self._on_cat_item_weight_changed('item_cat_foods_store', path, text)

    def on_item_cat_foods_add_clicked(self, *args):
        self._on_cat_item_add_clicked('item_cat_foods_store')

    def on_item_cat_foods_remove_clicked(self, *args):
        self._on_cat_item_remove_clicked('item_cat_foods_tree')

    def on_cr_items_cat_hold_item_name_edited(self, widget, path, text):
        self._on_cat_item_name_changed('item_cat_hold_store', path, text)

    def on_cr_items_cat_hold_item_name_editing_started(self, renderer, editable, path):
        editable.set_completion(self.builder.get_object('completion_item_hold'))

    def on_cr_items_cat_hold_guaranteed_toggled(self, widget, path):
        self._on_cat_item_guaranteed_toggled('item_cat_hold_store', path, widget.get_active())

    def on_cr_items_cat_hold_weight_edited(self, widget, path, text):
        self._on_cat_item_weight_changed('item_cat_hold_store', path, text)

    def on_item_cat_hold_add_clicked(self, *args):
        self._on_cat_item_add_clicked('item_cat_hold_store')

    def on_item_cat_hold_remove_clicked(self, *args):
        self._on_cat_item_remove_clicked('item_cat_hold_tree')

    def on_cr_items_cat_tms_item_name_edited(self, widget, path, text):
        self._on_cat_item_name_changed('item_cat_tms_store', path, text)

    def on_cr_items_cat_tms_item_name_editing_started(self, renderer, editable, path):
        editable.set_completion(self.builder.get_object('completion_item_tms'))

    def on_cr_items_cat_tms_guaranteed_toggled(self, widget, path):
        self._on_cat_item_guaranteed_toggled('item_cat_tms_store', path, widget.get_active())

    def on_cr_items_cat_tms_weight_edited(self, widget, path, text):
        self._on_cat_item_weight_changed('item_cat_tms_store', path, text)

    def on_item_cat_tms_add_clicked(self, *args):
        self._on_cat_item_add_clicked('item_cat_tms_store')

    def on_item_cat_tms_remove_clicked(self, *args):
        self._on_cat_item_remove_clicked('item_cat_tms_tree')

    def on_cr_items_cat_orbs_item_name_edited(self, widget, path, text):
        self._on_cat_item_name_changed('item_cat_orbs_store', path, text)

    def on_cr_items_cat_orbs_item_name_editing_started(self, renderer, editable, path):
        editable.set_completion(self.builder.get_object('completion_item_orbs'))

    def on_cr_items_cat_orbs_guaranteed_toggled(self, widget, path):
        self._on_cat_item_guaranteed_toggled('item_cat_orbs_store', path, widget.get_active())

    def on_cr_items_cat_orbs_weight_edited(self, widget, path, text):
        self._on_cat_item_weight_changed('item_cat_orbs_store', path, text)

    def on_item_cat_orbs_add_clicked(self, *args):
        self._on_cat_item_add_clicked('item_cat_orbs_store')

    def on_item_cat_orbs_remove_clicked(self, *args):
        self._on_cat_item_remove_clicked('item_cat_orbs_tree')

    def on_cr_items_cat_others_item_name_edited(self, widget, path, text):
        self._on_cat_item_name_changed('item_cat_others_store', path, text)

    def on_cr_items_cat_others_item_name_editing_started(self, renderer, editable, path):
        editable.set_completion(self.builder.get_object('completion_item_others'))

    def on_cr_items_cat_others_guaranteed_toggled(self, widget, path):
        self._on_cat_item_guaranteed_toggled('item_cat_others_store', path, widget.get_active())

    def on_cr_items_cat_others_weight_edited(self, widget, path, text):
        self._on_cat_item_weight_changed('item_cat_others_store', path, text)

    def on_item_cat_others_add_clicked(self, *args):
        self._on_cat_item_add_clicked('item_cat_others_store')

    def on_item_cat_others_remove_clicked(self, *args):
        self._on_cat_item_remove_clicked('item_cat_others_tree')

    def _on_cat_item_name_changed(self, store_name: str, path, text: str):
        store: Gtk.Store = self.builder.get_object(store_name)
        match = PATTERN_MD_ENTRY.match(text)
        if match is None:
            return

        item_ids_already_in = []
        for row in store:
            item_ids_already_in.append(int(row[0]))

        try:
            entid = int(match.group(1))
        except ValueError:
            return

        if entid not in CATEGORIES_FOR_STORES[store_name].item_ids():
            display_error(
                None,
                'This item does not belong in this category. Please chose another item.',
                'Invalid item id'
            )
            return

        if entid in item_ids_already_in:
            display_error(
                None,
                'This item is already in the list.',
                'Can not use this item'
            )
            return

        store[path][0] = entid
        store[path][1] = self._item_names[entid]
        self._save_item_spawn_rates()

    def _on_cat_item_guaranteed_toggled(self, store_name: str, path, old_state: bool):
        store: Gtk.Store = self.builder.get_object(store_name)
        store[path][2] = not old_state
        if not old_state:
            store[path][4] = "0"
        self._recalculate_spawn_chances(store_name, 4, 3)
        self._save_item_spawn_rates()

    def _on_cat_item_weight_changed(self, store_name: str, path, text: str):
        try:
            v = int(text)
            assert v >= 0
        except:
            return
        store: Gtk.Store = self.builder.get_object(store_name)
        if store[path][2]:
            return
        store[path][4] = text

        self._recalculate_spawn_chances(store_name, 4, 3)
        self._save_item_spawn_rates()

    def _on_cat_item_add_clicked(self, store_name: str):
        store: Gtk.ListStore = self.builder.get_object(store_name)

        item_ids_already_in = []
        for row in store:
            item_ids_already_in.append(int(row[0]))

        i = 0
        all_item_ids = CATEGORIES_FOR_STORES[store_name].item_ids()
        while True:
            first_item_id = all_item_ids[i]
            if first_item_id not in item_ids_already_in:
                break
            i += 1
            if i >= len(all_item_ids):
                display_error(
                    None,
                    'All items are already in the list',
                    'Can not add item.'
                )
                return
        store.append([
            first_item_id, self._item_names[first_item_id],
            False, "0%", "0"
        ])
        self._save_item_spawn_rates()

    def _on_cat_item_remove_clicked(self, tree_name: str):
        tree: Gtk.TreeView = self.builder.get_object(tree_name)
        model, treeiter = tree.get_selection().get_selected()
        if model is not None and treeiter is not None:
            model.remove(treeiter)
        self._recalculate_spawn_chances(Gtk.Buildable.get_name(tree.get_model()), 4, 3)
        self._save_item_spawn_rates()

    # </editor-fold>

    def on_btn_help__spawn_tables__clicked(self, *args):
        pass  # todo

    def on_item_list_notebook_switch_page(self, w: Gtk.Notebook, page: Gtk.Box, page_num: int, *args):
        self._item_list_edit_active = FloorEditItemList(page_num)
        self.__class__._last_open_tab_item_lists = FloorEditItemList(page_num)
        sw: Gtk.ScrolledWindow = self.builder.get_object('sw_item_editor')
        sw.get_parent().remove(sw)
        page.pack_start(sw, True, True, 0)
        self._init_item_spawns()

    def _init_labels(self):
        dungeon_name = self._string_provider.get_value(StringType.DUNGEON_NAMES_MAIN, self.item.dungeon.dungeon_id)
        self.builder.get_object(f'label_dungeon_name').set_text(
            f'Dungeon {self.item.dungeon.dungeon_id}\n{dungeon_name}'
        )
        self.builder.get_object('label_floor_number').set_text(f'Floor {self.item.floor_id + 1}')

    def _init_layout_stores(self):
        # cb_structure
        self._comboxbox_for_enum(['cb_structure'], MappaFloorStructureType)
        # cb_dead_ends
        self._comboxbox_for_boolean(['cb_dead_ends'])
        # cb_terrain_settings__generate_imperfect_rooms
        self._comboxbox_for_boolean(['cb_terrain_settings__generate_imperfect_rooms'])
        # cb_terrain_settings__has_secondary_terrain
        self._comboxbox_for_boolean(['cb_terrain_settings__has_secondary_terrain'])
        # cb_secondary_terrain
        self._comboxbox_for_enum(['cb_secondary_terrain'], MappaFloorSecondaryTerrainType)
        # cb_unk_e
        self._comboxbox_for_boolean(['cb_unk_e'])
        # cb_darkness_level
        self._comboxbox_for_enum(['cb_darkness_level'], MappaFloorDarknessLevel)
        # cb_weather
        self._comboxbox_for_enum(['cb_weather'], MappaFloorWeather)
        # cb_iq_booster_enabled
        self._comboxbox_for_boolean(['cb_iq_booster_enabled'])
        # cb_tileset_id
        self._comboxbox_for_tileset_id(['cb_tileset_id'])
        # cb_music_id
        self._comboxbox_for_music_id(['cb_music_id'])
        # cb_fixed_floor_id
        self._comboxbox_for_fixed_floor_id(['cb_fixed_floor_id'])

    def _init_layout_values(self):
        all_entries_and_cbs = [
            "cb_tileset_id",
            "cb_music_id",
            "cb_fixed_floor_id",
            "entry_room_density",
            "cb_structure",
            "entry_floor_connectivity",
            "cb_dead_ends",
            "entry_extra_hallway_density",
            "cb_terrain_settings__has_secondary_terrain",
            "cb_secondary_terrain",
            "cb_terrain_settings__generate_imperfect_rooms",
            "entry_water_density",
            "cb_darkness_level",
            "cb_weather",
            "entry_item_density",
            "entry_trap_density",
            "entry_initial_enemy_density",
            "entry_buried_item_density",
            "entry_max_coin_amount",
            "scale_kecleon_shop_chance",
            "scale_monster_house_chance",
            "scale_unusued_chance",
            "scale_hidden_stairs_spawn_chance",
            "entry_kecleon_shop_item_positions",
            "scale_empty_monster_house_chance",
            "scale_sticky_item_chance",
            "entry_unk_hidden_stairs",
            "cb_iq_booster_enabled",
            "entry_enemy_iq",
            "cb_unk_e"
        ]

        for w_name in all_entries_and_cbs:
            if w_name.startswith(CB):
                if w_name.startswith(CB_TERRAIN_SETTINGS):
                    val_key = w_name[len(CB_TERRAIN_SETTINGS):]
                    self._set_cb(w_name, getattr(self.entry.layout.terrain_settings, val_key))
                else:
                    val_key = w_name[len(CB):]
                    self._set_cb(w_name, getattr(self.entry.layout, val_key))
            elif w_name.startswith(ENTRY):
                if w_name.startswith(ENTRY_TERRAIN_SETTINGS):
                    val_key = w_name[len(ENTRY_TERRAIN_SETTINGS):]
                    self._set_entry(w_name, getattr(self.entry.layout.terrain_settings, val_key))
                else:
                    val_key = w_name[len(ENTRY):]
                    self._set_entry(w_name, getattr(self.entry.layout, val_key))
            else:
                val_key = w_name[len(SCALE):]
                self._set_scale(w_name, getattr(self.entry.layout, val_key))

    def _init_monster_spawns(self):
        self._init_monster_completion_store()
        store: Gtk.Store = self.builder.get_object('monster_spawns_store')
        # Add existing Pokémon
        relative_weights = self._calculate_relative_weights([x.weight for x in self.entry.monsters])
        sum_of_all_weights = sum(relative_weights)
        for i, monster in enumerate(self.entry.monsters):
            relative_weight = relative_weights[i]
            chance = f'{int(relative_weight) / sum_of_all_weights * 100:.3f}%'
            if monster.md_index == KECLEON_MD_INDEX:
                self.builder.get_object('kecleon_level_entry').set_text(str(monster.level))
                continue
            if monster.md_index == DUMMY_MD_INDEX:
                continue
            store.append([
                monster.md_index, self._get_icon(monster.md_index, i), self._ent_names[monster.md_index],
                str(monster.level), chance, str(relative_weight)
            ])

    def _init_monster_completion_store(self):
        monster_md = self.module.get_monster_md()
        monster_store: Gtk.ListStore = self.builder.get_object('completion_monsters_store')
        for idx, entry in enumerate(monster_md.entries[0:DUMMY_MD_INDEX]):
            if idx == 0:
                continue
            name = self.module.project.get_string_provider().get_value(StringType.POKEMON_NAMES, entry.md_index_base)
            self._ent_names[idx] = f'{name} (#{idx:03})'
            monster_store.append([self._ent_names[idx]])

    def _init_trap_spawns(self):
        store: Gtk.Store = self.builder.get_object('trap_spawns_store')
        # Add all traps
        relative_weights = self._calculate_relative_weights([x for x in self.entry.traps.weights.values()])
        sum_of_all_weights = sum(relative_weights)
        for i, (trap, weight) in enumerate(self.entry.traps.weights.items()):
            trap: MappaTrapType
            relative_weight = relative_weights[i]
            chance = f'{int(relative_weight) / sum_of_all_weights * 100:.3f}%'
            name = ' '.join([x.capitalize() for x in trap.name.split('_')])
            store.append([
                trap.value, name, chance, str(relative_weight)
            ])

    def _init_item_spawns(self):
        self._init_item_completion_store()

        item_categories_store: Gtk.ListStore = self.builder.get_object('item_categories_store')
        item_cat_thrown_pierce_store: Gtk.ListStore = self.builder.get_object('item_cat_thrown_pierce_store')
        item_cat_thrown_rock_store: Gtk.ListStore = self.builder.get_object('item_cat_thrown_rock_store')
        item_cat_berries_store: Gtk.ListStore = self.builder.get_object('item_cat_berries_store')
        item_cat_foods_store: Gtk.ListStore = self.builder.get_object('item_cat_foods_store')
        item_cat_hold_store: Gtk.ListStore = self.builder.get_object('item_cat_hold_store')
        item_cat_tms_store: Gtk.ListStore = self.builder.get_object('item_cat_tms_store')
        item_cat_orbs_store: Gtk.ListStore = self.builder.get_object('item_cat_orbs_store')
        item_cat_others_store: Gtk.ListStore = self.builder.get_object('item_cat_others_store')
        item_stores = {
            MappaItemCategory.THROWN_PIERCE: item_cat_thrown_pierce_store,
            MappaItemCategory.THROWN_ROCK: item_cat_thrown_rock_store,
            MappaItemCategory.BERRIES_SEEDS_VITAMINS: item_cat_berries_store,
            MappaItemCategory.FOODS_GUMMIES: item_cat_foods_store,
            MappaItemCategory.HOLD: item_cat_hold_store,
            MappaItemCategory.TMS: item_cat_tms_store,
            MappaItemCategory.ORBS: item_cat_orbs_store,
            MappaItemCategory.OTHER: item_cat_others_store
        }

        # Clear everything
        for s in [item_categories_store] + list(item_stores.values()):
            s.clear()

        il = self.get_current_item_list()

        # Add item categories
        relative_weights = self._calculate_relative_weights(list(il.categories.values()))
        sum_of_all_weights = sum(relative_weights)
        for i, (category, chance) in enumerate(il.categories.items()):
            relative_weight = relative_weights[i]
            if category not in VALID_ITEM_CATEGORY_NAMES:
                continue  # TODO: Support editing unknown / unused item categories?
            name = VALID_ITEM_CATEGORY_NAMES[category]
            chance = f'{int(relative_weight) / sum_of_all_weights * 100:.3f}%'
            item_categories_store.append([
                category.value, name, False,
                chance, str(relative_weight)
            ])

        # Add items
        items_by_category = self._split_items_in_list_in_cats(il.items)
        for j, (category, store) in enumerate(item_stores.items()):
            cat_items = items_by_category[category]
            relative_weights = self._calculate_relative_weights([v for v in cat_items.values() if v != GUARANTEED])
            sum_of_all_weights = sum(relative_weights)
            i = 0
            for item, stored_weight in cat_items.items():
                relative_weight = 0
                if stored_weight != GUARANTEED:
                    relative_weight = relative_weights[i]
                    i += 1
                name = self._item_names[item.id]
                chance = f'{int(relative_weight) / sum_of_all_weights * 100:.3f}%'
                store.append([
                    item.id, name, stored_weight == GUARANTEED,
                    chance, str(relative_weight)
                ])

    def _split_items_in_list_in_cats(
            self, items: Dict[Pmd2DungeonItem, Probability]
    ) -> Dict[MappaItemCategory, Dict[Pmd2DungeonItem, Probability]]:
        out_items = {}
        for cat in VALID_ITEM_CATEGORY_NAMES.keys():
            out_items[cat] = {}
            for item, probability in items.items():
                if cat.is_item_in_cat(item.id):
                    out_items[cat][item] = probability
        return out_items

    def _init_item_completion_store(self):
        completion_item_thrown_pierce_store: Gtk.ListStore = self.builder.get_object('completion_item_thrown_pierce_store')
        completion_item_thrown_rock_store: Gtk.ListStore = self.builder.get_object('completion_item_thrown_rock_store')
        completion_item_berries_store: Gtk.ListStore = self.builder.get_object('completion_item_berries_store')
        completion_item_foods_store: Gtk.ListStore = self.builder.get_object('completion_item_foods_store')
        completion_item_hold_store: Gtk.ListStore = self.builder.get_object('completion_item_hold_store')
        completion_item_tms_store: Gtk.ListStore = self.builder.get_object('completion_item_tms_store')
        completion_item_orbs_store: Gtk.ListStore = self.builder.get_object('completion_item_orbs_store')
        completion_item_others_store: Gtk.ListStore = self.builder.get_object('completion_item_others_store')
        completion_stores = {
            MappaItemCategory.THROWN_PIERCE: completion_item_thrown_pierce_store,
            MappaItemCategory.THROWN_ROCK: completion_item_thrown_rock_store,
            MappaItemCategory.BERRIES_SEEDS_VITAMINS: completion_item_berries_store,
            MappaItemCategory.FOODS_GUMMIES: completion_item_foods_store,
            MappaItemCategory.HOLD: completion_item_hold_store,
            MappaItemCategory.TMS: completion_item_tms_store,
            MappaItemCategory.ORBS: completion_item_orbs_store,
            MappaItemCategory.OTHER: completion_item_others_store
        }

        for i in range(0, MAX_ITEM_ID):
            name = self.module.project.get_string_provider().get_value(StringType.ITEM_NAMES, i)
            self._item_names[i] = f'{name} (#{i:03})'

        for category, store in completion_stores.items():
            for item in category.item_ids():
                store.append([self._item_names[item]])

    def _calculate_relative_weights(self, list_of_weights: List[int]) -> List[int]:
        weights = []
        if len(list_of_weights) < 1:
            return []
        for i in range(0, len(list_of_weights)):
            weight = list_of_weights[i]
            if weight != 0:
                last_nonzero = i - 1
                while last_nonzero >= 0 && list_of_weights[last_nonzero] == 0:
                    last_nonzero -= 1
                if last_nonzero != -1:
                    weight -= list_of_weights[last_nonzero]
            weights.append(weight)
        weights_lcm = reduce(gcd, (w for w in weights if w != 0))
        return [int(w / weights_lcm) for w in weights]

    def _recalculate_spawn_chances(self, store_name, weight_idx, chance_idx):
        store: Gtk.ListStore = self.builder.get_object(store_name)
        sum_of_all_weights = sum(int(row[weight_idx]) for row in store)
        for row in store:
            if sum_of_all_weights == 0:
                row[chance_idx] = '0.00%'
            else:
                row[chance_idx] = f'{int(row[weight_idx]) / sum_of_all_weights * 100:.2f}%'

    # TODO: Generalize this with the base classs for lists
    def _get_icon(self, entid, idx):
        was_loading = self._loading
        sprite, x, y, w, h = self._sprite_provider.get_monster(entid, 0,
                                                               lambda: GLib.idle_add(
                                                                   partial(self._reload_icon, entid, idx, was_loading)
                                                               ))
        data = bytes(sprite.get_data())
        # this is painful.
        new_data = bytearray()
        for b, g, r, a in grouper(data, 4):
            new_data += bytes([r, g, b, a])
        return GdkPixbuf.Pixbuf.new_from_data(
            new_data, GdkPixbuf.Colorspace.RGB, True, 8, w, h, sprite.get_stride()
        )

    def _reload_icon(self, entid, idx, was_loading):
        store: Gtk.Store = self.builder.get_object('monster_spawns_store')
        if not self._loading and not was_loading:
            row = store[idx]
            row[1] = self._get_icon(entid, idx)
            return
        if self._refresh_timer is not None:
            GLib.source_remove(self._refresh_timer)
        self._refresh_timer = GLib.timeout_add_seconds(0.5, self._reload_icons_in_tree)

    def _reload_icons_in_tree(self):
        store: Gtk.Store = self.builder.get_object('monster_spawns_store')
        self._loading = True
        for i, entry in enumerate(store):
            entry[1] = self._get_icon(entry[0], i)
        self._loading = False
        self._refresh_timer = None

    def _save_monster_spawn_rates(self):
        store: Gtk.ListStore = self.builder.get_object('monster_spawns_store')
        original_kecleon_level = 0
        for monster in self.entry.monsters:
            if monster.md_index == KECLEON_MD_INDEX:
                original_kecleon_level = monster.level
                break
        self.entry.monsters = []
        rows = []
        for row in store:
            rows.append(row[:])
        rows.append([KECLEON_MD_INDEX, None, None, str(original_kecleon_level), None, "0"])
        rows.append([DUMMY_MD_INDEX, None, None, "1", None, "0"])
        rows.sort(key=lambda e: e[0])

        sum_of_weights = sum((int(row[5]) for row in rows))

        last_weight = 0
        last_weight_set_idx = 0
        for i, row in enumerate(rows):
            weight = 0
            if row[5] != "0":
                weight = last_weight + int(10000 * (int(row[5]) / sum_of_weights))
                last_weight = weight
                last_weight_set_idx = i
            self.entry.monsters.append(MappaMonster(
                md_index=row[0],
                level=int(row[3]),
                weight=weight,
                weight2=weight
            ))
        if last_weight != 0 and last_weight != 10000:
            # We did not sum up to exactly 10000, so the values we entered are not evenly
            # divisible. Find the last non-zero we set and set it to 10000.
            self.entry.monsters[last_weight_set_idx].weight = 10000
            self.entry.monsters[last_weight_set_idx].weight2 = 10000
        self.mark_as_modified()

    def _save_trap_spawn_rates(self):
        store: Gtk.ListStore = self.builder.get_object('trap_spawns_store')

        sum_of_weights = sum((int(row[3]) for row in store))

        last_weight = 0
        last_weight_set_idx = 0
        weights = []
        for i, row in enumerate(store):
            weight = 0
            if row[3] != "0":
                weight = last_weight + int(10000 * (int(row[3]) / sum_of_weights))
                last_weight = weight
                last_weight_set_idx = i
            weights.append(weight)
        if last_weight != 0 and last_weight != 10000:
            # We did not sum up to exactly 10000, so the values we entered are not evenly
            # divisible. Find the last non-zero we set and set it to 10000.
            weights[last_weight_set_idx] = 10000
        self.entry.traps = MappaTrapList(weights)
        self.mark_as_modified()

    def _save_item_spawn_rates(self):
        item_stores = {
            None: self.builder.get_object('item_categories_store'),
            MappaItemCategory.THROWN_PIERCE: self.builder.get_object('item_cat_thrown_pierce_store'),
            MappaItemCategory.THROWN_ROCK: self.builder.get_object('item_cat_thrown_rock_store'),
            MappaItemCategory.BERRIES_SEEDS_VITAMINS: self.builder.get_object('item_cat_berries_store'),
            MappaItemCategory.FOODS_GUMMIES: self.builder.get_object('item_cat_foods_store'),
            MappaItemCategory.HOLD: self.builder.get_object('item_cat_hold_store'),
            MappaItemCategory.TMS: self.builder.get_object('item_cat_tms_store'),
            MappaItemCategory.ORBS: self.builder.get_object('item_cat_orbs_store'),
            MappaItemCategory.OTHER: self.builder.get_object('item_cat_others_store')
        }

        category_weights = {}
        item_weights = {}
        for (cat, store) in item_stores.items():

            rows = []
            for row in store:
                rows.append(row[:])
            rows.sort(key=lambda e: e[0])

            sum_of_weights = sum((int(row[4]) for row in store if row[2] is False))

            last_weight = 0
            last_weight_set_idx = None
            for i, row in enumerate(rows):

                # Add Poké and Link Box items for those categories
                if not cat:
                    if i == MappaItemCategory.POKE.value:
                        item_weights[Pmd2DungeonItem(MappaItemCategory.POKE.item_ids()[0], '')] = 10000
                    if i == MappaItemCategory.LINK_BOX.value:
                        item_weights[Pmd2DungeonItem(MappaItemCategory.LINK_BOX.item_ids()[0], '')] = 10000
                was_set = False
                weight = 0
                if row[2]:
                    weight = GUARANTEED
                else:
                    if row[4] != "0":
                        weight = last_weight + int(10000 * (int(row[4]) / sum_of_weights))
                        last_weight = weight
                        was_set = True
                if cat is None:
                    set_idx = MappaItemCategory(row[0])
                    category_weights[set_idx] = weight
                    if was_set:
                        last_weight_set_idx = set_idx
                else:
                    set_idx = Pmd2DungeonItem(row[0], '')
                    item_weights[Pmd2DungeonItem(row[0], '')] = weight
                    if was_set:
                        last_weight_set_idx = set_idx
            if last_weight_set_idx is not None:
                if last_weight != 0 and last_weight != 10000:
                    # We did not sum up to exactly 10000, so the values we entered are not evenly
                    # divisible. Find the last non-zero we set and set it to 10000.
                    if cat is None:
                        category_weights[last_weight_set_idx] = 10000
                    else:
                        item_weights[last_weight_set_idx] = 10000

        item_weights = {k: v for k, v in sorted(item_weights.items(), key=lambda x: x[0].id)}

        il = self.get_current_item_list()
        il.categories = category_weights
        il.items = item_weights

        self.mark_as_modified()

    def mark_as_modified(self):
        if not self._loading:
            self.module.mark_floor_as_modified(self.item)

    def _comboxbox_for_enum(self, names: List[str], enum: Type[Enum]):
        store = Gtk.ListStore(int, str)  # id, name
        for entry in enum:
            store.append([entry.value, self._enum_entry_to_str(entry)])
        for name in names:
            self._fast_set_comboxbox_store(self.builder.get_object(name), store, 1)

    def _comboxbox_for_boolean(self, names: List[str]):
        store = Gtk.ListStore(int, str)  # id, name
        store.append([0, "No"])
        store.append([1, "Yes"])
        for name in names:
            self._fast_set_comboxbox_store(self.builder.get_object(name), store, 1)

    def _comboxbox_for_tileset_id(self, names: List[str]):
        # TODO: For tilesets > 169(?) show names of map bgs.
        store = Gtk.ListStore(int, str)  # id, name
        for i in range(0, COUNT_VALID_TILESETS):
            store.append([i, f"Tileset {i}"])
        for name in names:
            self._fast_set_comboxbox_store(self.builder.get_object(name), store, 1)

    def _comboxbox_for_music_id(self, names: List[str]):
        # TODO: Music Name
        store = Gtk.ListStore(int, str)  # id, name
        for i in range(0, COUNT_VALID_BGM):
            store.append([i, f"{i} - NAME"])
        for name in names:
            self._fast_set_comboxbox_store(self.builder.get_object(name), store, 1)

    def _comboxbox_for_fixed_floor_id(self, names: List[str]):
        store = Gtk.ListStore(int, str)  # id, name
        store.append([0, f"No fixed floor"])
        for i in range(1, COUNT_VALID_FIXED_FLOORS):
            store.append([i, f"No. {i}"])
        for name in names:
            self._fast_set_comboxbox_store(self.builder.get_object(name), store, 1)

    @staticmethod
    def _fast_set_comboxbox_store(cb: Gtk.ComboBox, store: Gtk.ListStore, col):
        cb.set_model(store)
        renderer_text = Gtk.CellRendererText()
        cb.pack_start(renderer_text, True)
        cb.add_attribute(renderer_text, "text", col)

    def _enum_entry_to_str(self, entry):
        if hasattr(entry, 'print_name'):
            return entry.print_name
        return entry.name.capitalize().replace('_', ' ')

    def _set_entry(self, entry_name, text):
        self.builder.get_object(entry_name).set_text(str(text))

    def _set_cb(self, cb_name, value):
        if isinstance(value, Enum):
            value = value.value
        cb: Gtk.ComboBox = self.builder.get_object(cb_name)
        l_iter: Gtk.TreeIter = cb.get_model().get_iter_first()
        while l_iter:
            row = cb.get_model()[l_iter]
            if row[0] == value:
                cb.set_active_iter(l_iter)
                return
            l_iter = cb.get_model().iter_next(l_iter)
        raise ValueError("Value not found for CB.")

    def _set_scale(self, scale_name, val):
        scale: Gtk.Scale = self.builder.get_object(scale_name)
        scale.set_value(int(val))

    def _update_from_widget(self, w: Gtk.Widget):
        if isinstance(w, Gtk.ComboBox):
            return self._update_from_cb(w)
        elif isinstance(w, Gtk.Entry):
            return self._update_from_entry(w)
        return self._update_from_scale(w)

    def _update_from_entry(self, w: Gtk.Entry):
        w_name = Gtk.Buildable.get_name(w)
        if w_name.startswith(ENTRY_TERRAIN_SETTINGS):
            obj = self.entry.layout.terrain_settings
            attr_name = w_name[len(ENTRY_TERRAIN_SETTINGS):]
        else:
            obj = self.entry.layout
            attr_name = w_name[len(ENTRY):]
        try:
            val = int(w.get_text())
        except ValueError:
            return
        setattr(obj, attr_name, val)

    def _update_from_cb(self, w: Gtk.ComboBox):
        w_name = Gtk.Buildable.get_name(w)
        if w_name.startswith(CB_TERRAIN_SETTINGS):
            obj = self.entry.layout.terrain_settings
            attr_name = w_name[len(CB_TERRAIN_SETTINGS):]
        else:
            obj = self.entry.layout
            attr_name = w_name[len(CB):]
        val = w.get_model()[w.get_active_iter()][0]
        current_val = getattr(obj, attr_name)
        if isinstance(current_val, Enum):
            enum_class = current_val.__class__
            val = enum_class(val)
        setattr(obj, attr_name, val)

    def _update_from_scale(self, w: Gtk.Scale):
        w_name = Gtk.Buildable.get_name(w)
        obj = self.entry.layout
        attr_name = w_name[len(SCALE):]
        val = int(w.get_value())
        setattr(obj, attr_name, val)

    def get_current_item_list(self) -> MappaItemList:
        if self._item_list_edit_active == FloorEditItemList.FLOOR:
            return self.entry.floor_items
        if self._item_list_edit_active == FloorEditItemList.SHOP:
            return self.entry.shop_items
        if self._item_list_edit_active == FloorEditItemList.MONSTER_HOUSE:
            return self.entry.monster_house_items
        if self._item_list_edit_active == FloorEditItemList.BURIED:
            return self.entry.buried_items
        if self._item_list_edit_active == FloorEditItemList.UNK1:
            return self.entry.unk_items1
        if self._item_list_edit_active == FloorEditItemList.UNK2:
            return self.entry.unk_items2


def grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return ((bytes(bytearray(x))) for x in zip_longest(fillvalue=fillvalue, *args))
