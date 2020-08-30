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
from enum import Enum
from typing import TYPE_CHECKING, List, Type

from gi.repository import Gtk

from skytemple.core.module_controller import AbstractController
from skytemple.core.string_provider import StringType
from skytemple_files.dungeon_data.mappa_bin.floor_layout import MappaFloorStructureType, MappaFloorSecondaryTerrainType, \
    MappaFloorDarknessLevel, MappaFloorWeather

if TYPE_CHECKING:
    from skytemple.module.dungeon.module import DungeonModule, FloorViewInfo


COUNT_VALID_TILESETS = 199
COUNT_VALID_BGM = 117
COUNT_VALID_FIXED_FLOORS = 256
CB = 'cb_'
CB_TERRAIN_SETTINGS = 'cb_terrain_settings__'
ENTRY = 'entry_'
ENTRY_TERRAIN_SETTINGS = 'entry_terrain_settings__'
SCALE = 'scale_'


class FloorController(AbstractController):
    _last_open_tab_id = 0

    def __init__(self, module: 'DungeonModule', item: 'FloorViewInfo'):
        self.module = module
        self.item = item
        self.entry = self.module.get_mappa_floor(item)

        self.builder = None
        self._is_loading = False
        self._string_provider = module.project.get_string_provider()
        self._sprite_provider = module.project.get_sprite_provider()

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'floor.glade')

        self._init_labels()
        self._init_layout_stores()

        self._is_loading = True
        self._init_layout_values()
        self._is_loading = False

        self.builder.connect_signals(self)
        # TODO: Dungeon mini preview

        notebook: Gtk.Notebook = self.builder.get_object('floor_notebook')
        notebook.set_current_page(self.__class__._last_open_tab_id)

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

    def on_entry_floor_connectivity_changed(self, w, *args):
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
        pass  # todo

    def on_cr_monster_spawns_entity_editing_started(self, renderer, editable, path):
        pass  # todo

    def on_cr_monster_spawns_chance_edited(self, widget, path, text):
        pass  # todo

    def on_cr_monster_spawns_level_edited(self, widget, path, text):
        pass  # todo

    def on_monster_spawns_add_clicked(self, *args):
        pass  # todo

    def on_monster_spawns_remove_clicked(self, *args):
        pass  # todo

    # </editor-fold>

    # <editor-fold desc="HANDLERS TRAPS" defaultstate="collapsed">

    def on_cr_trap_spawns_trap_edited(self, widget, path, text):
        pass  # todo

    def on_cr_trap_spawns_chance_edited(self, widget, path, text):
        pass  # todo

    # </editor-fold>

    # <editor-fold desc="ITEM HANDLERS" defaultstate="collapsed">

    def on_cr_items_cat_name_changed(self, widget, path, new_iter):
        pass  # todo

    def on_cr_items_cat_guaranteed_toggled(self, widget, path):
        pass  # todo

    def on_cr_items_cat_chance_edited(self, widget, path, text):
        pass  # todo

    def on_item_categories_add_clicked(self, *args):
        pass  # todo

    def on_item_categories_remove_clicked(self, *args):
        pass  # todo

    def on_cr_items_cat_thrown_pierce_item_name_edited(self, widget, path, text):
        pass  # todo

    def on_cr_items_cat_thrown_pierce_item_name_editing_started(self, renderer, editable, path):
        pass  # todo

    def on_cr_items_cat_thrown_pierce_guaranteed_toggled(self, widget, path):
        pass  # todo

    def on_cr_items_cat_thrown_pierce_chance_edited(self, widget, path, text):
        pass  # todo

    def on_item_cat_thrown_pierce_add_clicked(self, *args):
        pass  # todo

    def on_item_cat_thrown_pierce_remove_clicked(self, *args):
        pass  # todo

    def on_cr_items_cat_thrown_rock_item_name_edited(self, widget, path, text):
        pass  # todo

    def on_cr_items_cat_thrown_rock_item_name_editing_started(self, renderer, editable, path):
        pass  # todo

    def on_cr_items_cat_thrown_rock_guaranteed_toggled(self, widget, path):
        pass  # todo

    def on_cr_items_cat_thrown_rock_chance_edited(self, widget, path, text):
        pass  # todo

    def on_item_cat_thrown_rock_add_clicked(self, *args):
        pass  # todo

    def on_item_cat_thrown_rock_remove_clicked(self, *args):
        pass  # todo

    def on_cr_items_cat_berries_item_name_edited(self, widget, path, text):
        pass  # todo

    def on_cr_items_cat_berries_item_name_editing_started(self, renderer, editable, path):
        pass  # todo

    def on_cr_items_berries_rock_guaranteed_toggled(self, widget, path):
        pass  # todo

    def on_cr_items_cat_berries_chance_edited(self, widget, path, text):
        pass  # todo

    def on_item_cat_berries_add_clicked(self, *args):
        pass  # todo

    def on_item_cat_berries_remove_clicked(self, *args):
        pass  # todo

    def on_cr_items_cat_foods_item_name_edited(self, widget, path, text):
        pass  # todo

    def on_cr_items_cat_foods_item_name_editing_started(self, renderer, editable, path):
        pass  # todo

    def on_cr_items_cat_foods_guaranteed_toggled(self, widget, path):
        pass  # todo

    def on_cr_items_cat_foods_chance_edited(self, widget, path, text):
        pass  # todo

    def on_item_cat_foods_add_clicked(self, *args):
        pass  # todo

    def on_item_cat_foods_remove_clicked(self, *args):
        pass  # todo

    def on_cr_items_cat_hold_item_name_edited(self, widget, path, text):
        pass  # todo

    def on_cr_items_cat_hold_item_name_editing_started(self, renderer, editable, path):
        pass  # todo

    def on_cr_items_cat_hold_guaranteed_toggled(self, widget, path):
        pass  # todo

    def on_cr_items_cat_hold_chance_edited(self, widget, path, text):
        pass  # todo

    def on_item_cat_hold_add_clicked(self, *args):
        pass  # todo

    def on_item_cat_hold_remove_clicked(self, *args):
        pass  # todo

    def on_cr_items_cat_tms_item_name_edited(self, widget, path, text):
        pass  # todo

    def on_cr_items_cat_tms_item_name_editing_started(self, renderer, editable, path):
        pass  # todo

    def on_cr_items_cat_tms_guaranteed_toggled(self, widget, path):
        pass  # todo

    def on_cr_items_cat_tms_chance_edited(self, widget, path, text):
        pass  # todo

    def on_item_cat_tms_add_clicked(self, *args):
        pass  # todo

    def on_item_cat_tms_remove_clicked(self, *args):
        pass  # todo

    def on_cr_items_cat_orbs_item_name_edited(self, widget, path, text):
        pass  # todo

    def on_cr_items_cat_orbs_item_name_editing_started(self, renderer, editable, path):
        pass  # todo

    def on_cr_items_cat_orbs_guaranteed_toggled(self, widget, path):
        pass  # todo

    def on_cr_items_cat_orbs_chance_edited(self, widget, path, text):
        pass  # todo

    def on_item_cat_orbs_add_clicked(self, *args):
        pass  # todo

    def on_item_cat_orbs_remove_clicked(self, *args):
        pass  # todo

    def on_cr_items_cat_others_item_name_edited(self, widget, path, text):
        pass  # todo

    def on_cr_items_cat_others_item_name_editing_started(self, renderer, editable, path):
        pass  # todo

    def on_cr_items_cat_others_guaranteed_toggled(self, widget, path):
        pass  # todo

    def on_cr_items_cat_others_chance_edited(self, widget, path, text):
        pass  # todo

    def on_item_cat_others_add_clicked(self, *args):
        pass  # todo

    def on_item_cat_others_remove_clicked(self, *args):
        pass  # todo

    # </editor-fold>

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

    def mark_as_modified(self):
        if not self._is_loading:
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
