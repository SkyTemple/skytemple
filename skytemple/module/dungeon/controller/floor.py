#  Copyright 2020-2021 Capypara and the SkyTemple Contributors
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
import logging
import random
import re
import sys
import traceback
from enum import Enum
from functools import partial, reduce
from itertools import zip_longest
from math import gcd
from typing import TYPE_CHECKING, List, Type, Dict, Tuple, Optional
from xml.etree import ElementTree

from gi.repository import Gtk, GLib, GdkPixbuf

from skytemple.controller.main import MainController
from skytemple.core.error_handler import display_error
from skytemple.core.list_icon_renderer import ListIconRenderer
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.module_controller import AbstractController
from skytemple.core.open_request import OpenRequest, REQUEST_TYPE_DUNGEON_TILESET, REQUEST_TYPE_DUNGEON_FIXED_FLOOR, \
    REQUEST_TYPE_DUNGEON_MUSIC
from skytemple.core.string_provider import StringType
from skytemple.core.ui_utils import add_dialog_xml_filter, glib_async
from skytemple.module.dungeon import COUNT_VALID_TILESETS, TILESET_FIRST_BG
from skytemple.module.dungeon.controller.dojos import DOJOS_NAME
from skytemple.module.dungeon.fixed_room_drawer import FixedRoomDrawer
from skytemple.module.dungeon.fixed_room_entity_renderer.full_map import FullMapEntityRenderer
from skytemple.module.dungeon.fixed_room_entity_renderer.minimap import MinimapEntityRenderer
from skytemple.module.dungeon.fixed_room_tileset_renderer.bg import FixedFloorDrawerBackground
from skytemple.module.dungeon.fixed_room_tileset_renderer.minimap import FixedFloorDrawerMinimap
from skytemple.module.dungeon.fixed_room_tileset_renderer.tileset import FixedFloorDrawerTileset
from skytemple.module.dungeon.minimap_provider import MinimapProvider
from skytemple_files.common.dungeon_floor_generator.generator import DungeonFloorGenerator, SIZE_X, SIZE_Y, Tile, \
    TileType, RandomGenProperties, RoomType
from skytemple_files.common.ppmdu_config.dungeon_data import Pmd2DungeonItem, Pmd2DungeonItemCategory
from skytemple_files.common.xml_util import prettify
from skytemple_files.dungeon_data.fixed_bin.model import FixedFloor, DirectRule
from skytemple_files.dungeon_data.mappa_bin.floor_layout import MappaFloorStructureType, \
    MappaFloorDarknessLevel, MappaFloorWeather
from skytemple_files.dungeon_data.mappa_bin.item_list import MappaItemList, Probability, GUARANTEED, \
    MAX_ITEM_ID, POKE_ID
from skytemple_files.dungeon_data.mappa_bin.mappa_xml import mappa_floor_xml_export
from skytemple_files.dungeon_data.mappa_bin.monster import DUMMY_MD_INDEX, MappaMonster
from skytemple_files.dungeon_data.mappa_bin.trap_list import MappaTrapType, MappaTrapList
from skytemple.controller.main import MainController as SkyTempleMainController
from skytemple_files.common.i18n_util import _, f

if TYPE_CHECKING:
    from skytemple.module.dungeon.module import DungeonModule, FloorViewInfo

COUNT_VALID_BGM = 118
COUNT_VALID_FIXED_FLOORS = 256
KECLEON_MD_INDEX = [383, 983]
CB = 'cb_'
CB_TERRAIN_SETTINGS = 'cb_terrain_settings__'
ENTRY = 'entry_'
ENTRY_TERRAIN_SETTINGS = 'entry_terrain_settings__'
SCALE = 'scale_'
PATTERN_MD_ENTRY = re.compile(r'.*\(#(\d+)\).*')
CSS_HEADER_COLOR = 'dungeon_editor_column_header_invalid'
POKE_CATEGORY_ID = 6
LINKBOX_CATEGORY_ID = 10
logger = logging.getLogger(__name__)


class FloorEditItemList(Enum):
    FLOOR = 0
    SHOP = 1
    MONSTER_HOUSE = 2
    BURIED = 3
    UNK1 = 4
    UNK2 = 5

class FloorRanks(Enum):
    INVALID = 0, _("Invalid")
    E_RANK = 1, _("E Rank")
    D_RANK = 2, _("D Rank")
    C_RANK = 3, _("C Rank")
    B_RANK = 4, _("B Rank")
    A_RANK = 5, _("A Rank")
    S_RANK = 6, _("S Rank")
    S1_RANK = 7, _("★1 Rank")
    S2_RANK = 8, _("★2 Rank")
    S3_RANK = 9, _("★3 Rank")
    S4_RANK = 10, _("★4 Rank")
    S5_RANK = 11, _("★5 Rank")
    S6_RANK = 12, _("★6 Rank")
    S7_RANK = 13, _("★7 Rank")
    S8_RANK = 14, _("★8 Rank")
    S9_RANK = 15, _("★9 Rank")

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    # ignore the first param since it's already set by __new__
    def __init__(self, _: str, print_name: str = None):
        self._print_name_ = print_name

    def __str__(self):
        return self._print_name_

    def __repr__(self):
        return f'FloorRanks.{self.name}'

    @property
    def print_name(self):
        return self._print_name_


class FloorController(AbstractController):
    _last_open_tab_id = 0
    _last_open_tab_item_lists = FloorEditItemList.FLOOR
    _last_scale_factor = None
    _last_show_full_map = False

    def __init__(self, module: 'DungeonModule', item: 'FloorViewInfo'):
        self.module = module
        self.item = item
        self.entry = self.module.get_mappa_floor(item)

        self.builder = None
        self._draw = None
        self._refresh_timer = None
        self._loading = False
        self._string_provider = module.project.get_string_provider()
        self._sprite_provider = module.project.get_sprite_provider()

        if self.__class__._last_scale_factor is not None:
            self._scale_factor = self.__class__._last_scale_factor
        else:
            self._scale_factor = 2

        self._item_list_edit_active = self.__class__._last_open_tab_item_lists

        self._ent_names = {}
        self._item_names = {}
        orig_cats = module.project.get_rom_module().get_static_data().dungeon_data.item_categories

        # TODO: Support editing other item categories?
        self.item_categories = {
            0: orig_cats[0],
            1: orig_cats[1],
            2: orig_cats[2],
            3: orig_cats[3],
            4: orig_cats[4],
            5: orig_cats[5],
            6: orig_cats[6],
            8: orig_cats[8],
            9: orig_cats[9],
            10: orig_cats[10],
        }
        self.categories_for_stores = {
            'item_cat_thrown_pierce_store': orig_cats[0],
            'item_cat_thrown_rock_store': orig_cats[1],
            'item_cat_berries_store': orig_cats[2],
            'item_cat_foods_store': orig_cats[3],
            'item_cat_hold_store': orig_cats[4],
            'item_cat_tms_store': orig_cats[5],
            'item_cat_orbs_store': orig_cats[9],
            'item_cat_others_store': orig_cats[8]
        }

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

        if not self.module.project.is_patch_applied("ExpandPokeList"):
            self.builder.get_object('switch_kecleon_gender').destroy()
            self.builder.get_object('label_kecleon_gender').destroy()
        self._init_layout_values()
        self._loading = False

        # Preview
        self._draw = self.builder.get_object('fixed_draw')
        self._init_drawer()
        tool_fullmap = self.builder.get_object('tool_fullmap')
        tool_fullmap.set_active(self._last_show_full_map)
        self.on_tool_fullmap_toggled(tool_fullmap, ignore_scaling=True)
        self._generate_floor()

        self.builder.connect_signals(self)

        notebook: Gtk.Notebook = self.builder.get_object('floor_notebook')
        notebook.set_current_page(self.__class__._last_open_tab_id)

        item_list_notebook: Gtk.Notebook = self.builder.get_object('item_list_notebook')
        item_list_notebook.set_current_page(self._item_list_edit_active.value)

        return self.builder.get_object('box_editor')

    def unload(self):
        # We need to destroy this first.
        # GTK is an enigma sometimes.
        self.builder.get_object('export_dialog').destroy()
        super().unload()
        self.drawer.unload()
        self.module = None
        self.item = None
        self.entry = None
        self.builder = None
        self._draw = None
        self._refresh_timer = None
        self._loading = False
        self._string_provider = None
        self._sprite_provider = None
        self._scale_factor = None
        self._item_list_edit_active = None
        self._ent_names = {}
        self._item_names = {}

    # <editor-fold desc="HANDLERS LAYOUT" defaultstate="collapsed">

    def on_floor_notebook_switch_page(self, notebook, page, page_num):
        self.__class__._last_open_tab_id = page_num
        if page_num == 0:
            self._generate_floor()

    def on_cb_floor_ranks_changed(self, w, *args):
        if self.module.has_floor_ranks():
            cb = self.builder.get_object('cb_floor_ranks')
            self.module.set_floor_rank(self.item.dungeon.dungeon_id, self.item.floor_id, cb.get_active())
            self.mark_as_modified()

    def on_btn_help_floor_ranks_clicked(self, *args):
        self._help(_("This attribute is the base rank of this floor. \n"
                     "The floor rank determines the item list used for mission rewards and treasure boxes content. \n"
                     "Needs the 'ExtractDungeonData' patch to be applied to edit this attribute."))
        
    def on_cb_mission_forbidden_changed(self, w, *args):
        if self.module.has_floor_ranks():
            cb = self.builder.get_object('cb_mission_forbidden')
            self.module.set_floor_mf(self.item.dungeon.dungeon_id, self.item.floor_id, cb.get_active())
            self.mark_as_modified()
            
    def on_btn_help_mission_forbidden_clicked(self, *args):
        self._help(_("If this attribute is set to 'Yes', no missions will be generated for this floor, and Wonder Mail S codes targetting this floor will be considered as invalid. \n"
                     "Needs the 'ExtractDungeonData' patch to be applied to edit this attribute."))
        
    def on_cb_tileset_id_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified(modified_mappag=True)
        if self.builder.get_object('tool_auto_refresh').get_active() and self.builder.get_object('tool_fullmap').get_active():
            self._init_tileset()

    def on_cb_music_id_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_cb_fixed_floor_id_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified(modified_mappag=True)

    def on_entry_room_density_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_btn_help_room_density_clicked(self, *args):
        self._help(_("The game randomly adds a number between 0 and 2 to obtain the final value."))

    def on_cb_structure_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_cb_dead_ends_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_btn_help_dead_ends_clicked(self, *args):
        self._help(_("Controls whether dead end hallways can be generated in the floor. "
                     "Dead ends can still appear in the map even if they are disabled due to a bug in the "
                     "map generator and because extra hallways can also produce them."))

    def on_entry_floor_connectivity_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_entry_water_density_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_btn_help_water_density_clicked(self, *args):
        self._help(_("This is the amount of lakes that will be generated during the water generation phase."))

    def on_entry_extra_hallway_density_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_btn_help_floor_connectivity_clicked(self, *args):
        self._help(_("Floor connectivity (Min 1, if it's 0 a valid map can't be generated and you will get the default "
                     "single room that it's also a monster house).\n\n"
                     "This is the amount of connections between cells that will be generated when the map is first "
                     "created. More will be added later to ensure that all the rooms can be accessed.\n"
                     "A cell is a point in the initial grid used to generate the map. It will end up being a room or a "
                     "crossroad once the full map is generated."))

    def on_btn_help_extra_hallway_density_clicked(self, *args):
        self._help(_("Used to generate additional hallways in the map (those \"donuts\" that lead to nowhere, multiple "
                     "entrances to the same room, room exits connected to the same room, those dead ends that come out "
                     "of a room, make a couple of twists and also lead to nowhere)"))

    def on_cb_terrain_settings__has_secondary_terrain_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_entry_secondary_terrain_changed(self, w, *args):
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

    def on_btn_help_trap_density_clicked(self, *args):
        self._help(_("The final value is randomized between density and density/2."))

    def on_btn_help_max_coin_amount_clicked(self, *args):
        self._help(_("The value stored in the ROM is actually the value divided by 5. Because of this the saved value "
                     "will be rounded to the next multiple of 5."))

    def on_btn_help_chances_clicked(self, *args):
        self._help(_("These sliders control how likely it is (in %) for certain things to generate on this floor."))

    def on_btn_help_kecleon_shop_item_positions_clicked(self, *args):
        self._help(_("Every Kecleon shop has a minimum amount of guaranteed items.\n"
                     "This value controls where in the shop they will be placed."))

    def on_btn_help_unk_hidden_stairs_clicked(self, *args):
        self._help(_("0 --> 100% secret bazaar\n"
                     "1 --> 100% secret room\n"
                     "255 --> 50% secret bazaar, 50% secret room\n"
                     "Other values: 0% secret bazaar, 0% secret room (you just go to the next floor like normal stairs)."))

    def on_scale_kecleon_shop_chance_value_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_scale_monster_house_chance_value_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_scale_unusued_chance_value_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_btn_help_unusued_chance_clicked(self, *args):
        self._help(_("Does not work in the game. To make it work, apply the \"UnusedDungeonChancePatch\" from "
                     "\"ASM Patches.\"\nIf patched, the game will turn a random room into a maze room made of wall tiles "
                     "instead of the usual water (although water can later replace some of the walls once the water "
                     "generation takes place)."))

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
        self._help(_("It was added in explorers of sky, so right now it's only used in the sky exclusive dungeons.\n"
                     "If a monster house spawns in the floor, this is the chance of it being empty (no items will be "
                     "generated inside)."))

    def on_scale_sticky_item_chance_value_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_entry_unk_hidden_stairs_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_entry_iq_booster_boost_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_btn_help_iq_booster_boost_clicked(self, *args):
        self._help(_("If more than 0, the IQ booster increases IQ on this floor by this amount."))

    def on_entry_enemy_iq_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_cb_unk_e_changed(self, w, *args):
        self._update_from_widget(w)
        self.mark_as_modified()

    def on_btn_goto_tileset_clicked(self, *args):
        idx = self.builder.get_object('cb_tileset_id').get_active()
        self.module.project.request_open(OpenRequest(
            REQUEST_TYPE_DUNGEON_TILESET, idx
        ))

    def on_btn_goto_fixed_floor_clicked(self, *args):
        idx = self.builder.get_object('cb_fixed_floor_id').get_active()
        if idx > 0:
            self.module.project.request_open(OpenRequest(
                REQUEST_TYPE_DUNGEON_FIXED_FLOOR, idx
            ))

    def on_btn_goto_music_clicked(self, *args):
        self.module.project.request_open(OpenRequest(
            REQUEST_TYPE_DUNGEON_MUSIC, None
        ))

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

        if entid in KECLEON_MD_INDEX or entid==DUMMY_MD_INDEX:
            display_error(
                None,
                f(_("You can not spawn Kecleons or the Decoy Pokémon.")),
                _("SkyTemple: Invalid Pokémon")
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
            if monster.md_index in KECLEON_MD_INDEX:
                monster.level = level
                break
        self.mark_as_modified()

    def on_switch_kecleon_gender_state_set(self, w, *args):
        if w.get_active():
            new_index = KECLEON_MD_INDEX[1]
        else:
            new_index = KECLEON_MD_INDEX[0]
        for i, monster in enumerate(self.entry.monsters):
            if monster.md_index in KECLEON_MD_INDEX:
                monster.md_index = new_index
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

    @glib_async
    def on_cr_items_cat_name_changed(self, widget, path, new_iter, *args):
        store: Gtk.Store = self.builder.get_object('item_categories_store')
        cb_store: Gtk.Store = self.builder.get_object('cr_item_cat_name_store')
        store[path][0] = cb_store[new_iter][0]
        store[path][1] = cb_store[new_iter][1]
        self._save_item_spawn_rates()
        self._update_cr_item_cat_name_store()

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
        cb_store: Gtk.ListStore = self.builder.get_object('category_add_store')
        cb: Gtk.ComboBoxText = self.builder.get_object('category_add_cb')
        available_categories = self._fill_available_categories_into_store(cb_store)
        # Show error if no categories available
        if len(available_categories) < 1:
            display_error(
                None,
                _('All categories are already in the list.'),
                _('Can not add category')
            )
            return
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
            self._update_cr_item_cat_name_store()

    def on_item_categories_remove_clicked(self, *args):
        tree: Gtk.TreeView = self.builder.get_object('item_categories_tree')
        model, treeiter = tree.get_selection().get_selected()
        if len(model) < 2:
            display_error(
                None,
                _("The last category can not be removed."),
                _("Can't remove category.")
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

        if entid not in self.categories_for_stores[store_name].item_ids():
            display_error(
                None,
                _('This item does not belong in this category. Please chose another item.'),
                _('Invalid item id')
            )
            return

        if entid in item_ids_already_in:
            display_error(
                None,
                _('This item is already in the list.'),
                _('Can not use this item')
            )
            return

        store[path][0] = entid
        store[path][1] = self._item_names[entid]
        item_icon_renderer = ListIconRenderer(5)
        itm = self.module.get_item(entid)
        ##################
        ##################
        # DO NOT LOOK
        # this is awful
        liter = store.get_iter_first()
        i = 0
        found = False
        while liter:
            # dear god what is this
            if str(store.get_path(liter)) == path:
                found = True
                break
            liter = store.iter_next(liter)
            i += 1
        row_idx = i
        assert found
        # end of awfulness
        ##################
        ##################
        item_icon = item_icon_renderer.load_icon(
            store, self.module.project.get_sprite_provider().get_for_item, row_idx, row_idx, (itm,)
        )
        store[path][5] = item_icon
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
        all_item_ids = self.categories_for_stores[store_name].item_ids()
        while True:
            first_item_id = all_item_ids[i]
            if first_item_id not in item_ids_already_in:
                break
            i += 1
            if i >= len(all_item_ids):
                display_error(
                    None,
                    _('All items are already in the list'),
                    _('Can not add item.')
                )
                return
        item_icon_renderer = ListIconRenderer(5)
        itm = self.module.get_item(first_item_id)
        row_idx = len(store)
        item_icon = item_icon_renderer.load_icon(
            store, self.module.project.get_sprite_provider().get_for_item, row_idx, row_idx, (itm,)
        )
        store.append([
            first_item_id, self._item_names[first_item_id],
            False, "0%", "0", item_icon
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

    # <editor-fold desc="PREVIEW" defaultstate="collapsed">

    def on_tool_scene_zoom_in_clicked(self, *args):
        self._scale_factor *= 2
        self.__class__._last_scale_factor = self._scale_factor
        self._update_scales()

    def on_tool_scene_zoom_out_clicked(self, *args):
        self._scale_factor /= 2
        self.__class__._last_scale_factor = self._scale_factor
        self._update_scales()

    def on_tool_scene_grid_toggled(self, w: Gtk.ToggleButton):
        if self.drawer:
            self.drawer.set_draw_tile_grid(w.get_active())

    def on_tool_fullmap_toggled(self, w: Gtk.ToggleToolButton, *args, ignore_scaling=False):
        self.__class__._last_show_full_map = w.get_active()
        if w.get_active():
            if not ignore_scaling:
                self._scale_factor /= 10
                self.__class__._last_scale_factor = self._scale_factor
            self.drawer.set_entity_renderer(FullMapEntityRenderer(self.drawer))
            self._init_tileset()
        else:
            if not ignore_scaling:
                self._scale_factor *= 10
                self.__class__._last_scale_factor = self._scale_factor
            minimap_provider = MinimapProvider(self.module.get_zmappa())
            self.drawer.set_entity_renderer(MinimapEntityRenderer(self.drawer, minimap_provider))
            self.drawer.set_tileset_renderer(FixedFloorDrawerMinimap(minimap_provider))
        self._update_scales()
        self._draw.queue_draw()

    def _init_drawer(self):
        self.drawer = FixedRoomDrawer(self._draw, None, self.module.project.get_sprite_provider(),
                                      None, self.module.project.get_string_provider(), self.module)
        self.drawer.start()

        self.drawer.set_draw_tile_grid(self.builder.get_object(f'tool_scene_grid').get_active())

    def _generate_floor(self):
        stack: Gtk.Stack = self.builder.get_object('preview_stack')
        try:
            try:
                rng = random.Random(int(self.builder.get_object('tool_entry_seed').get_text()))
            except ValueError:
                rng = random.Random(hash(self.builder.get_object('tool_entry_seed').get_text()))

            floor: List[Tile] = DungeonFloorGenerator(
                unknown_dungeon_chance_patch_applied=self.module.project.is_patch_applied('UnusedDungeonChancePatch'),
                gen_properties=RandomGenProperties.default(rng)
            ).generate(self.entry.layout, max_retries=3, flat=True)
            if floor is None:
                stack.set_visible_child(self.builder.get_object('preview_error_infinite'))
                return
            stack.set_visible_child(self._draw)
            item_cats = self.module.project.get_rom_module().get_static_data().dungeon_data.item_categories
            actions = []
            warnings = set()
            open_guaranteed_floor = set(x.id for x, y in self.entry.floor_items.items.items() if y == GUARANTEED)
            open_guaranteed_buried = set(x.id for x, y in self.entry.buried_items.items.items() if y == GUARANTEED)
            for x in floor:
                idx = None
                if x.typ == TileType.PLAYER_SPAWN:
                    idx = self._sprite_provider.get_standin_entities()[0]
                if x.typ == TileType.ENEMY:
                    ridx = rng.randrange(0, 10000)
                    last = KECLEON_MD_INDEX  # fallback
                    invalid = True
                    for m in self.entry.monsters:
                        if m.weight > ridx and m.weight != 0:
                            last = m.md_index
                            invalid = False
                            break
                    if invalid:
                        warnings.add(_("Warning: Some Pokémon spawns may be invalid. Kecleons will been spawned instead."))
                    idx = last
                if x.typ == TileType.ITEM and len(open_guaranteed_floor) > 0:
                    idx = open_guaranteed_floor.pop()
                if x.typ == TileType.BURIED_ITEM and len(open_guaranteed_buried) > 0:
                    idx = open_guaranteed_buried.pop()
                if x.typ == TileType.ITEM or x.typ == TileType.BURIED_ITEM:
                    ridx_cat = rng.randrange(0, 10000)
                    ridx_itm = rng.randrange(0, 10000)
                    last_cat = POKE_CATEGORY_ID  # fallback
                    last_item = POKE_ID  # fallback
                    invalid_cat = True
                    invalid_itm = True
                    item_list = self.entry.floor_items
                    if x.typ == TileType.BURIED_ITEM:
                        item_list = self.entry.buried_items
                    for c, prop in item_list.categories.items():
                        if prop > ridx_cat and prop != 0:
                            last_cat = c.value
                            invalid_cat = False
                            break
                    for itm, prop in item_list.items.items():
                        if prop > ridx_itm and prop != GUARANTEED and prop != 0 and itm.id in item_cats[last_cat].item_ids():
                            last_item = itm.id
                            invalid_itm = False
                            break
                    if invalid_cat or invalid_itm:
                        warnings.add(_("Warning: Some Item spawns may be invalid. Poké will been spawned instead."))
                    idx = last_item
                if x.typ == TileType.TRAP:
                    ridx = rng.randrange(0, 10000)
                    last = 0  # fallback
                    invalid = True
                    for trap, weight in self.entry.traps.weights.items():
                        if weight > ridx and weight != 0:
                            last = trap.value
                            invalid = False
                            break
                    if invalid:
                        warnings.add(_("Warning: Some traps spawns may be invalid. Unused traps will been spawned instead."))
                    idx = last
                actions.append(DirectRule(x, idx))
            self.drawer.fixed_floor = FixedFloor.new(SIZE_Y, SIZE_X, actions)
            if self.entry.layout.fixed_floor_id > 0:
                self.builder.get_object('tool_label_info').set_text((_("Note: Floor uses a fixed room, the preview doesn't take this into account.\n") + '\n'.join(warnings)).strip('\n'))
            else:
                self.builder.get_object('tool_label_info').set_text('\n'.join(warnings))
            self._update_scales()
        except Exception as ex:
            logger.error('Preview loading error', exc_info=ex)
            tb: Gtk.TextBuffer = self.builder.get_object('preview_error_buffer')
            tb.set_text(''.join(traceback.format_exception(etype=type(ex), value=ex, tb=ex.__traceback__)))
            stack.set_visible_child(self.builder.get_object('preview_error'))


    def _init_tileset(self):
        if self.entry.layout.tileset_id < TILESET_FIRST_BG:
            # Real tileset
            self.drawer.set_tileset_renderer(FixedFloorDrawerTileset(*self.module.get_dungeon_tileset(self.entry.layout.tileset_id)))
        else:
            # Background to render using dummy tileset
            self.drawer.set_tileset_renderer(FixedFloorDrawerBackground(
                *self.module.get_dungeon_background(self.entry.layout.tileset_id - TILESET_FIRST_BG),
                *self.module.get_dummy_tileset())
            )

    def _update_scales(self):
        if self.drawer.fixed_floor is not None:
            self._draw.set_size_request(
                (self.drawer.fixed_floor.width + 10) * self.drawer.tileset_renderer.chunk_dim() * self._scale_factor,
                (self.drawer.fixed_floor.height + 10) * self.drawer.tileset_renderer.chunk_dim() * self._scale_factor
            )
            if self.drawer:
                self.drawer.set_scale(self._scale_factor)

            self._draw.queue_draw()

    def on_tool_refresh_clicked(self, *args):
        self._generate_floor()

    def on_tool_entry_seed_changed(self, *args):
        if self.builder.get_object('tool_auto_refresh').get_active():
            self._generate_floor()

    def on_btn_help_tool_seed_clicked(self, *args):
        self._help(_("This seed is used as the base to randomly generate the actual seeds used by the "
                     "dungeon generation engine. Note that generated previews might not be 100% accurate."))

    # </editor-fold>

    def on_btn_help__spawn_tables__clicked(self, *args):
        self._help(_("Change the chances of Pokémon, traps or items spawning.\nThe spawn chance depends on the weight "
                     "of an entry. The higher an entry's weight is, the more likely it is to spawn.\n"
                     "Please note for Pokémon, that weights for Pokémon that can not be spawned (eg. legendaries "
                     "without having their items) will be added to the next Pokémon entry in the list when the game "
                     "decides what to spawn.\n"
                     "Please note for items, that the game first decides what category to spawn for an item and then "
                     "chooses an entry for that category.\n"
                     "All spawn entries are always saved to the game sorted by their (Pokémon, item, trap) ID."))

    def on_btn_export_clicked(self, *args):
        # TODO: Add export for Ranks and Forbidden Missions attributes
        from skytemple.module.dungeon.module import DungeonGroup, ICON_GROUP, \
            ICON_DUNGEONS, DOJO_DUNGEONS_FIRST, DOJO_DUNGEONS_LAST
        dialog: Gtk.Dialog = self.builder.get_object('export_dialog')
        dialog.resize(460, 560)
        dialog.set_attached_to(SkyTempleMainController.window())
        dialog.set_transient_for(SkyTempleMainController.window())

        # Fill dungeon tree
        store: Gtk.TreeStore = self.builder.get_object('export_dialog_store')
        store.clear()
        for dungeon_or_group in self.module.load_dungeons():
            if isinstance(dungeon_or_group, DungeonGroup):
                # Group
                group = store.append(None, [
                    -1, -1, False, ICON_GROUP,
                    self.module.generate_group_label(dungeon_or_group.base_dungeon_id), False, False
                ])
                for dungeon, start_id in zip(dungeon_or_group.dungeon_ids, dungeon_or_group.start_ids):
                    self._add_dungeon_to_export_dialog_tree(group, store, dungeon, start_id)
            else:
                # Dungeon
                self._add_dungeon_to_export_dialog_tree(None, store, dungeon_or_group, 0)

        # Dojo dungeons
        dojo_root = store.append(None, [
            -1, -1, False, ICON_DUNGEONS,
            DOJOS_NAME, False, False
        ])
        for i in range(DOJO_DUNGEONS_FIRST, DOJO_DUNGEONS_LAST + 1):
            self._add_dungeon_to_export_dialog_tree(dojo_root, store, i, 0)

        resp = dialog.run()
        dialog.hide()

        if resp == Gtk.ResponseType.APPLY:
            # Create output XML
            xml = mappa_floor_xml_export(
                self.entry,
                export_layout=self.builder.get_object('export_type_layout').get_active(),
                export_monsters=self.builder.get_object('export_type_monsters').get_active(),
                export_traps=self.builder.get_object('export_type_traps').get_active(),
                export_floor_items=self.builder.get_object('export_type_floor_items').get_active(),
                export_shop_items=self.builder.get_object('export_type_shop_items').get_active(),
                export_monster_house_items=self.builder.get_object('export_type_monster_house_items').get_active(),
                export_buried_items=self.builder.get_object('export_type_buried_items').get_active(),
                export_unk1_items=self.builder.get_object('export_type_unk_items1').get_active(),
                export_unk2_items=self.builder.get_object('export_type_unk_items2').get_active()
            )

            # 1. Export to file
            if self.builder.get_object('export_file_switch').get_active():
                save_diag = Gtk.FileChooserNative.new(
                    _("Export floor as..."),
                    SkyTempleMainController.window(),
                    Gtk.FileChooserAction.SAVE,
                    None, None
                )

                add_dialog_xml_filter(save_diag)
                response = save_diag.run()
                fn = save_diag.get_filename()
                if '.' not in fn:
                    fn += '.xml'
                save_diag.destroy()

                if response == Gtk.ResponseType.ACCEPT:
                    with open(fn, 'w') as f:
                        f.write(prettify(xml))
                else:
                    md = SkyTempleMessageDialog(SkyTempleMainController.window(),
                                                Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.WARNING,
                                                Gtk.ButtonsType.OK, _("Export was canceled."))
                    md.set_position(Gtk.WindowPosition.CENTER)
                    md.run()
                    md.destroy()
                    return

            # 2. Import to selected floors
            selected_floors: List[Tuple[int, int]] = []
            def collect_floors_recurse(titer: Optional[Gtk.TreeIter]):
                for i in range(store.iter_n_children(titer)):
                    child = store.iter_nth_child(titer, i)
                    if store[child][2] and store[child][5]:  # is floor and is selected
                        selected_floors.append((store[child][0], store[child][1]))
                    collect_floors_recurse(child)

            collect_floors_recurse(None)
            self.module.import_from_xml(selected_floors, xml)

    def on_btn_import_clicked(self, *args):
        # TODO: Add import for Ranks and Forbidden Missions attributes
        
        save_diag = Gtk.FileChooserNative.new(
            _("Import floor from..."),
            SkyTempleMainController.window(),
            Gtk.FileChooserAction.OPEN,
            None, None
        )

        add_dialog_xml_filter(save_diag)
        response = save_diag.run()
        fn = save_diag.get_filename()
        save_diag.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            try:
                self.module.import_from_xml([(self.item.dungeon.dungeon_id, self.item.floor_id)],
                                            ElementTree.parse(fn).getroot())
                SkyTempleMainController.reload_view()
            except BaseException as err:
                display_error(
                    sys.exc_info(),
                    str(err),
                    _("Error importing the floor.")
                )

    def on_cr_export_selected_toggled(self, w: Gtk.CellRendererToggle, path, *args):
        store: Gtk.TreeStore = self.builder.get_object('export_dialog_store')
        is_active = not w.get_active()
        store[path][5] = is_active
        store[path][6] = False
        # Update inconsistent state for all parents
        def mark_inconsistent_recurse(titer: Gtk.TreeIter, force_inconstent=False):
            parent = store.iter_parent(titer)
            if parent is not None:
                should_be_inconsistent = force_inconstent
                if not should_be_inconsistent:
                    # Look at children to see if should be marked inconsistent
                    children = []
                    for i in range(store.iter_n_children(parent)):
                        child = store.iter_nth_child(parent, i)
                        children.append(child)
                    states = [store[child][5] for child in children]
                    should_be_inconsistent = any([store[child][6] for child in children]) or not states.count(states[0]) == len(states)
                store[parent][6] = should_be_inconsistent
                if should_be_inconsistent:
                    store[parent][5] = False
                else:
                    store[parent][5] = states[0]
                mark_inconsistent_recurse(parent, should_be_inconsistent)

        mark_inconsistent_recurse(store.get_iter(path))
        # Update state for all children
        def mark_active_recurse(titer: Gtk.TreeIter):
            for i in range(store.iter_n_children(titer)):
                child = store.iter_nth_child(titer, i)
                store[child][5] = is_active
                store[child][6] = False
                mark_active_recurse(child)
        mark_active_recurse(store.get_iter(path))

    def on_item_list_notebook_switch_page(self, w: Gtk.Notebook, page: Gtk.Box, page_num: int, *args):
        self._item_list_edit_active = FloorEditItemList(page_num)
        self.__class__._last_open_tab_item_lists = FloorEditItemList(page_num)
        sw: Gtk.ScrolledWindow = self.builder.get_object('sw_item_editor')
        sw.get_parent().remove(sw)
        page.pack_start(sw, True, True, 0)
        self._init_item_spawns()

    def _add_dungeon_to_export_dialog_tree(self, root_node, item_store, idx, previous_floor_id):
        from skytemple.module.dungeon.module import ICON_DUNGEON
        dungeon = item_store.append(root_node, [
            -1, -1, False, ICON_DUNGEON,
            self.module.generate_dungeon_label(idx), False, False
        ])
        for floor_i in range(0, self.module.get_number_floors(idx)):
            item_store.append(dungeon, [
                idx, previous_floor_id + floor_i, True, ICON_DUNGEON,
                self.module.generate_floor_label(floor_i + previous_floor_id), False, False
            ])
        return dungeon

    def _init_labels(self):
        dungeon_name = self._string_provider.get_value(StringType.DUNGEON_NAMES_MAIN, self.item.dungeon.dungeon_id)
        self.builder.get_object(f'label_dungeon_name').set_text(
            f'{"Dungeon"} {self.item.dungeon.dungeon_id}\n{dungeon_name}'
        )
        self.builder.get_object('label_floor_number').set_text(f'{"Floor"} {self.item.floor_id + 1}')

    def _init_layout_stores(self):
        # cb_structure
        self._comboxbox_for_enum(['cb_structure'], MappaFloorStructureType)
        # cb_dead_ends
        self._comboxbox_for_boolean(['cb_dead_ends'])
        # cb_terrain_settings__generate_imperfect_rooms
        self._comboxbox_for_boolean(['cb_terrain_settings__generate_imperfect_rooms'])
        # cb_terrain_settings__has_secondary_terrain
        self._comboxbox_for_boolean(['cb_terrain_settings__has_secondary_terrain'])
        # cb_unk_e
        self._comboxbox_for_boolean(['cb_unk_e'])
        # cb_darkness_level
        self._comboxbox_for_enum(['cb_darkness_level'], MappaFloorDarknessLevel)
        # cb_weather
        self._comboxbox_for_enum(['cb_weather'], MappaFloorWeather)
        # cb_tileset_id
        self._comboxbox_for_tileset_id(['cb_tileset_id'])
        # cb_music_id
        self._comboxbox_for_music_id(['cb_music_id'])
        # cb_fixed_floor_id
        self._comboxbox_for_fixed_floor_id(['cb_fixed_floor_id'])
        if self.module.has_floor_ranks():
            # cb_floor_ranks
            self._comboxbox_for_enum(['cb_floor_ranks'], FloorRanks)
        else:
            self.builder.get_object('cb_floor_ranks').set_sensitive(False)
        if self.module.has_mission_forbidden():
            # cb_mission_forbidden
            self._comboxbox_for_boolean(['cb_mission_forbidden'])
        else:
            self.builder.get_object('cb_mission_forbidden').set_sensitive(False)

    def _init_layout_values(self):
        cb = self.builder.get_object('cb_floor_ranks')
        if self.item.dungeon.length_can_be_edited and self.module.has_floor_ranks():
            cb.set_active(self.module.get_floor_rank(self.item.dungeon.dungeon_id, self.item.floor_id))
        else:
            cb.set_sensitive(False)
        cb = self.builder.get_object('cb_mission_forbidden')
        if self.item.dungeon.length_can_be_edited and self.module.has_mission_forbidden():
            cb.set_active(self.module.get_floor_mf(self.item.dungeon.dungeon_id, self.item.floor_id))
        else:
            cb.set_sensitive(False)
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
            "entry_secondary_terrain",
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
            "entry_iq_booster_boost",
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
        if sum_of_all_weights <= 0:
            sum_of_all_weights = 1  # all weights are zero, so we just set this to 1 so it doesn't / by 0.
        for i, monster in enumerate(self.entry.monsters):
            relative_weight = relative_weights[i]
            chance = f'{int(relative_weight) / sum_of_all_weights * 100:.3f}%'
            if monster.md_index in KECLEON_MD_INDEX:
                self.builder.get_object('kecleon_level_entry').set_text(str(monster.level))
                switch = self.builder.get_object('switch_kecleon_gender')
                if monster.md_index==KECLEON_MD_INDEX[0]:
                    switch.set_active(False)
                else:
                    switch.set_active(True)
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
        for idx, entry in enumerate(monster_md.entries):
            if idx == 0:
                continue
            name = self.module.project.get_string_provider().get_value(StringType.POKEMON_NAMES, entry.md_index_base)
            self._ent_names[idx] = f'{name} (#{idx:03})'
            monster_store.append([self._ent_names[idx]])

    def _init_trap_spawns(self):
        store: Gtk.Store = self.builder.get_object('trap_spawns_store')
        trap_icon_renderer = ListIconRenderer(4)
        # Add all traps
        relative_weights = self._calculate_relative_weights([x for x in self.entry.traps.weights.values()])
        sum_of_all_weights = sum(relative_weights)
        if sum_of_all_weights <= 0:
            sum_of_all_weights = 1  # all weights are zero, so we just set this to 1 so it doesn't / by 0.
        for i, (trap, weight) in enumerate(self.entry.traps.weights.items()):
            trap: MappaTrapType
            relative_weight = relative_weights[i]
            chance = f'{int(relative_weight) / sum_of_all_weights * 100:.3f}%'
            trap_icon = trap_icon_renderer.load_icon(
                store, self.module.project.get_sprite_provider().get_for_trap, i, i, (trap, )
            )
            store.append([
                trap.value, trap.name, chance, str(relative_weight), trap_icon
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
            self.item_categories[0]: item_cat_thrown_pierce_store,
            self.item_categories[1]: item_cat_thrown_rock_store,
            self.item_categories[2]: item_cat_berries_store,
            self.item_categories[3]: item_cat_foods_store,
            self.item_categories[4]: item_cat_hold_store,
            self.item_categories[5]: item_cat_tms_store,
            self.item_categories[9]: item_cat_orbs_store,
            self.item_categories[8]: item_cat_others_store
        }

        # Clear everything
        for s in [item_categories_store] + list(item_stores.values()):
            s.clear()

        il = self.get_current_item_list()

        # Add item categories
        relative_weights = self._calculate_relative_weights(list(il.categories.values()))
        sum_of_all_weights = sum(relative_weights)
        if sum_of_all_weights <= 0:
            sum_of_all_weights = 1  # all weights are zero, so we just set this to 1 so it doesn't / by 0.
        for i, (category, chance) in enumerate(il.categories.items()):
            relative_weight = relative_weights[i]
            if category.value not in self.item_categories.keys():
                continue  # TODO: Support editing other item categories?
            name = self.item_categories[category.value].name_localized
            chance = f'{int(relative_weight) / sum_of_all_weights * 100:.3f}%'
            item_categories_store.append([
                category.value, name, False,
                chance, str(relative_weight)
            ])

        # Add items
        items_by_category = self._split_items_in_list_in_cats(il.items)
        for j, (category, store) in enumerate(item_stores.items()):
            item_icon_renderer = ListIconRenderer(5)
            cat_items = items_by_category[category]
            relative_weights = self._calculate_relative_weights([v for v in cat_items.values() if v != GUARANTEED])
            sum_of_all_weights = sum(relative_weights)
            if sum_of_all_weights <= 0:
                sum_of_all_weights = 1  # all weights are zero, so we just set this to 1 so it doesn't / by 0.
            i = 0
            for row_idx, (item, stored_weight) in enumerate(cat_items.items()):
                relative_weight = 0
                if stored_weight != GUARANTEED:
                    relative_weight = relative_weights[i]
                    i += 1
                name = self._item_names[item.id]
                chance = f'{int(relative_weight) / sum_of_all_weights * 100:.3f}%'
                itm = self.module.get_item(item.id)
                item_icon = item_icon_renderer.load_icon(
                    store, self.module.project.get_sprite_provider().get_for_item, row_idx, row_idx, (itm, )
                )
                store.append([
                    item.id, name, stored_weight == GUARANTEED,
                    chance, str(relative_weight), item_icon
                ])
        self._update_cr_item_cat_name_store()

    def _split_items_in_list_in_cats(
            self, items: Dict[Pmd2DungeonItem, Probability]
    ) -> Dict[Pmd2DungeonItemCategory, Dict[Pmd2DungeonItem, Probability]]:
        out_items = {}
        for cat in self.item_categories.values():
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
            self.item_categories[0]: completion_item_thrown_pierce_store,
            self.item_categories[1]: completion_item_thrown_rock_store,
            self.item_categories[2]: completion_item_berries_store,
            self.item_categories[3]: completion_item_foods_store,
            self.item_categories[4]: completion_item_hold_store,
            self.item_categories[5]: completion_item_tms_store,
            self.item_categories[9]: completion_item_orbs_store,
            self.item_categories[8]: completion_item_others_store
        }

        for i in range(0, MAX_ITEM_ID):
            name = self.module.project.get_string_provider().get_value(StringType.ITEM_NAMES, i)
            self._item_names[i] = f'{name} (#{i:03})'

        for category, store in completion_stores.items():
            for item in category.item_ids():
                if item < MAX_ITEM_ID:
                    store.append([self._item_names[item]])

    def _calculate_relative_weights(self, list_of_weights: List[int]) -> List[int]:
        weights = []
        if len(list_of_weights) < 1:
            return []
        for i in range(0, len(list_of_weights)):
            weight = list_of_weights[i]
            if weight != 0:
                last_nonzero = i - 1
                while last_nonzero >= 0 and list_of_weights[last_nonzero] == 0:
                    last_nonzero -= 1
                if last_nonzero != -1:
                    weight -= list_of_weights[last_nonzero]
            weights.append(weight)
        weights_nonzero = [w for w in weights if w != 0]
        weights_gcd = 1
        if len(weights_nonzero) > 0:
            weights_gcd = reduce(gcd, weights_nonzero)
        return [int(w / weights_gcd) for w in weights]

    def _recalculate_spawn_chances(self, store_name, weight_idx, chance_idx):
        store: Gtk.ListStore = self.builder.get_object(store_name)
        sum_of_all_weights = sum(int(row[weight_idx]) for row in store)
        if sum_of_all_weights <= 0:
            sum_of_all_weights = 1  # all weights are zero, so we just set this to 1 so it doesn't / by 0.
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
        try:
            store: Gtk.Store = self.builder.get_object('monster_spawns_store')
            self._loading = True
            for i, entry in enumerate(store):
                entry[1] = self._get_icon(entry[0], i)
            self._loading = False
            self._refresh_timer = None
        except (AttributeError, TypeError):
            pass  # This happens when the view was unloaded in the meantime.

    def _save_monster_spawn_rates(self):
        store: Gtk.ListStore = self.builder.get_object('monster_spawns_store')
        original_kecleon_level = 0
        original_kecleon_index = KECLEON_MD_INDEX[0]
        for monster in self.entry.monsters:
            if monster.md_index in KECLEON_MD_INDEX:
                original_kecleon_index = monster.md_index
                original_kecleon_level = monster.level
                break
        self.entry.monsters = []
        rows = []
        for row in store:
            rows.append(row[:])
        rows.append([original_kecleon_index, None, None, str(original_kecleon_level), None, "0"])
        rows.append([DUMMY_MD_INDEX, None, None, "1", None, "0"])
        rows.sort(key=lambda e: e[0])

        sum_of_weights = sum((int(row[5]) for row in rows))

        last_weight = 0
        last_weight_set_idx = 0
        for i, row in enumerate(rows):
            weight = 0
            if int(row[5]) != 0:
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
            if int(row[3]) != 0:
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

    def _fill_available_categories_into_store(self, cb_store):
        available_categories = [
            cat for cat in self.item_categories.values()
            if cat not in self.get_current_item_list().categories.keys()
        ]
        # Init combobox
        cb_store.clear()
        for cat in available_categories:
            cb_store.append([cat.value, cat.name_localized])
        return available_categories

    def _update_cr_item_cat_name_store(self):
        store = self.builder.get_object('cr_item_cat_name_store')
        self._fill_available_categories_into_store(store)

    def _save_item_spawn_rates(self):
        item_stores = {
            None: self.builder.get_object('item_categories_store'),
            self.item_categories[0]: self.builder.get_object('item_cat_thrown_pierce_store'),
            self.item_categories[1]: self.builder.get_object('item_cat_thrown_rock_store'),
            self.item_categories[2]: self.builder.get_object('item_cat_berries_store'),
            self.item_categories[3]: self.builder.get_object('item_cat_foods_store'),
            self.item_categories[4]: self.builder.get_object('item_cat_hold_store'),
            self.item_categories[5]: self.builder.get_object('item_cat_tms_store'),
            self.item_categories[9]: self.builder.get_object('item_cat_orbs_store'),
            self.item_categories[8]: self.builder.get_object('item_cat_others_store')
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
            for row in rows:
                # Add Poké and Link Box items for those categories
                if not cat:
                    if row[0] == POKE_CATEGORY_ID:
                        item_weights[Pmd2DungeonItem(self.item_categories[POKE_CATEGORY_ID].item_ids()[0], '')] = 10000
                    if row[0] == LINKBOX_CATEGORY_ID:
                        item_weights[Pmd2DungeonItem(self.item_categories[LINKBOX_CATEGORY_ID].item_ids()[0], '')] = 10000
                was_set = False
                weight = 0
                if row[2]:
                    weight = GUARANTEED
                else:
                    if int(row[4]) != 0:
                        weight = last_weight + int(10000 * (int(row[4]) / sum_of_weights))
                        last_weight = weight
                        was_set = True
                if cat is None:
                    set_idx = self.item_categories[row[0]]
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

    def mark_as_modified(self, modified_mappag = False):
        if not self._loading:
            self.module.mark_floor_as_modified(self.item, modified_mappag)

    def _comboxbox_for_enum(self, names: List[str], enum: Type[Enum]):
        store = Gtk.ListStore(int, str)  # id, name
        for entry in enum:
            store.append([entry.value, self._enum_entry_to_str(entry)])
        for name in names:
            self._fast_set_comboxbox_store(self.builder.get_object(name), store, 1)

    def _comboxbox_for_boolean(self, names: List[str]):
        store = Gtk.ListStore(int, str)  # id, name
        store.append([0, _("No")])
        store.append([1, _("Yes")])
        for name in names:
            self._fast_set_comboxbox_store(self.builder.get_object(name), store, 1)

    def _comboxbox_for_tileset_id(self, names: List[str]):
        store = Gtk.ListStore(int, str)  # id, name
        for i in range(0, COUNT_VALID_TILESETS):
            if i >= TILESET_FIRST_BG:
                store.append([i, f"{'Background'} {i}"])
            else:
                store.append([i, f"{'Tileset'} {i}"])
        for name in names:
            self._fast_set_comboxbox_store(self.builder.get_object(name), store, 1)

    def _comboxbox_for_music_id(self, names: List[str]):
        store = Gtk.ListStore(int, str)  # id, name
        music_entries = self.module.project.get_rom_module().get_static_data().script_data.bgms__by_id
        dungeon_music, random_tracks = self.module.get_dungeon_music_spec()
        for i, track in enumerate(dungeon_music):
            if track.is_random_ref:
                name = _("Random ") + str(track.track_or_ref)
            else:
                if track.track_or_ref == 999:
                    name = _("Invalid?")
                elif track.track_or_ref >= len(music_entries):
                    name = _("INVALID!!!")
                else:
                    if len(music_entries[track.track_or_ref].name) > 10:
                        name = music_entries[track.track_or_ref].name[:10] + '...'
                    else:
                        name = music_entries[track.track_or_ref].name
            store.append([i, name + f" (#{i:03})"])
        for name in names:
            self._fast_set_comboxbox_store(self.builder.get_object(name), store, 1)

    def _comboxbox_for_fixed_floor_id(self, names: List[str]):
        store = Gtk.ListStore(int, str)  # id, name
        store.append([0, _("No fixed room")])
        for i in range(1, COUNT_VALID_FIXED_FLOORS):
            store.append([i, f(_("No. {i}"))])  # TRANSLATORS: Number {i}
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
            self._update_from_cb(w)
        elif isinstance(w, Gtk.Entry):
            self._update_from_entry(w)
        else:
            self._update_from_scale(w)
        if self.builder.get_object('tool_auto_refresh').get_active():
            self._generate_floor()

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

    def _help(self, msg):
        md = SkyTempleMessageDialog(MainController.window(),
                                    Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                    Gtk.ButtonsType.OK, msg)
        md.run()
        md.destroy()


def grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return ((bytes(bytearray(x))) for x in zip_longest(fillvalue=fillvalue, *args))
