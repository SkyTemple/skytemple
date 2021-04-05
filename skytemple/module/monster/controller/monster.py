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
import logging
import math
import re
from enum import Enum
from typing import TYPE_CHECKING, Type, List, Optional, Dict
from xml.etree import ElementTree

import cairo
from gi.repository import Gtk, GLib

from skytemple.controller.main import MainController
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.module_controller import AbstractController
from skytemple.core.string_provider import StringType
from skytemple.core.ui_utils import add_dialog_xml_filter
from skytemple.module.monster.controller.level_up import LevelUpController
from skytemple.module.portrait.portrait_provider import IMG_DIM
from skytemple_files.common.types.file_types import FileType
from skytemple_files.common.xml_util import prettify
from skytemple_files.data.md.model import Gender, PokeType, MovementType, IQGroup, Ability, EvolutionMethod, \
    AdditionalRequirement, NUM_ENTITIES, ShadowSize, MONSTER_BIN, MdEntry
from skytemple.controller.main import MainController as SkyTempleMainController
from skytemple_files.data.monster_xml import monster_xml_export
from skytemple_files.common.i18n_util import f, _

if TYPE_CHECKING:
    from skytemple.module.monster.module import MonsterModule
MAX_ITEMS = 1400
PATTERN = re.compile(r'.*\(#(\d+)\).*')
logger = logging.getLogger(__name__)


class MonsterController(AbstractController):
    _last_open_tab_id = 0

    def __init__(self, module: 'MonsterModule', item_id: int):
        self.module = module
        self.item_id = item_id
        self.entry = self.module.get_entry(self.item_id)

        self._monster_bin = self.module.project.open_file_in_rom(MONSTER_BIN, FileType.BIN_PACK, threadsafe=True)

        self.builder = None
        self._is_loading = False
        self._string_provider = module.project.get_string_provider()
        self._sprite_provider = module.project.get_sprite_provider()
        self._portrait_provider = module.project.get_module('portrait').get_portrait_provider()
        self._level_up_controller: Optional[LevelUpController] = None
        self._cached_sprite_page = None

        self._render_graph_on_tab_change = True

        self.item_names = {}
        for i in range(0, MAX_ITEMS):
            name = self.module.project.get_string_provider().get_value(StringType.ITEM_NAMES, i)
            self.item_names[i] = f'{name} (#{i:04})'

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'monster.glade')

        self._sprite_provider.reset()
        self._portrait_provider.reset()

        self._init_language_labels()
        self._init_entid()
        self._init_stores()
        self._init_sub_pages()

        # Init Items Completion
        store: Gtk.ListStore = self.builder.get_object('store_completion_items')

        for item in self.item_names.values():
            store.append([item])

        self._is_loading = True
        self._init_values()
        self._is_loading = False

        self._update_pre_evo_label()
        self._update_base_form_label()
        self._update_param_label()
        self._update_chance_label()

        self.builder.connect_signals(self)
        self.builder.get_object('draw_sprite').queue_draw()

        notebook: Gtk.Notebook = self.builder.get_object('main_notebook')
        notebook.set_current_page(self.__class__._last_open_tab_id)

        self._check_sprite_size(True)

        return self.builder.get_object('box_main')

    def on_main_notebook_switch_page(self, notebook, page, page_num):
        self.__class__._last_open_tab_id = page_num
        if self._render_graph_on_tab_change:
            self._render_graph_on_tab_change = False
            if self._level_up_controller is not None:
                try:
                    self._level_up_controller.render_graph()
                except AttributeError:
                    # ??? Sometimes it's None but still runs into here?
                    pass

    def on_draw_portrait_draw(self, widget: Gtk.DrawingArea, ctx: cairo.Context):
        scale = 2
        portrait = self._portrait_provider.get(self.entry.md_index - 1, 0,
                                               lambda: GLib.idle_add(widget.queue_draw), True)
        ctx.scale(scale, scale)
        ctx.set_source_surface(portrait)
        ctx.get_source().set_filter(cairo.Filter.NEAREST)
        ctx.paint()
        ctx.scale(1 / scale, 1 / scale)
        if widget.get_size_request() != (IMG_DIM * scale, IMG_DIM * scale):
            widget.set_size_request(IMG_DIM * scale, IMG_DIM * scale)
        return True

    def on_draw_sprite_draw(self, widget: Gtk.DrawingArea, ctx: cairo.Context):
        if self.entry.entid > 0:
            sprite, x, y, w, h = self._sprite_provider.get_monster(self.entry.md_index, 0,
                                                                   lambda: GLib.idle_add(widget.queue_draw))
        else:
            sprite, x, y, w, h = self._sprite_provider.get_error()
        ctx.set_source_surface(sprite)
        ctx.get_source().set_filter(cairo.Filter.NEAREST)
        ctx.paint()
        if widget.get_size_request() != (w, h):
            widget.set_size_request(w, h)
        return True

    def on_cb_type_primary_changed(self, w, *args):
        self._update_from_cb(w)
        self.mark_as_modified()

    def on_cb_type_secondary_changed(self, w, *args):
        self._update_from_cb(w)
        self.mark_as_modified()

    def on_entry_national_pokedex_number_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_entid_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_personality_changed(self, w, *args):
        try:
            self.module.set_personality(self.item_id, int(w.get_text()))
        except ValueError:
            pass
        
    def on_entry_sprite_index_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()
        self._sprite_provider.reset()
        self._check_sprite_size(False)
        self.builder.get_object('draw_sprite').queue_draw()
        self._reload_sprite_page()

    def on_cb_gender_changed(self, w, *args):
        self._update_from_cb(w)
        #Changing the gender should also refresh the tree, as the gender is marked here.
        self.module.refresh(self.item_id)
        self.mark_as_modified()

    def on_entry_lang1_changed(self, w, *args):
        self.builder.get_object('label_id_name').set_text(f'${self.entry.md_index:04d}: {w.get_text()}')
        self._update_lang_from_entry(w, 0)
        self.module.refresh(self.item_id)
        self.mark_as_modified()

    def on_entry_lang2_changed(self, w, *args):
        self._update_lang_from_entry(w, 1)
        self.mark_as_modified()

    def on_entry_lang3_changed(self, w, *args):
        self._update_lang_from_entry(w, 2)
        self.mark_as_modified()

    def on_entry_lang4_changed(self, w, *args):
        self._update_lang_from_entry(w, 3)
        self.mark_as_modified()

    def on_entry_lang5_changed(self, w, *args):
        self._update_lang_from_entry(w, 4)
        self.mark_as_modified()

    def on_entry_lang1_cat_changed(self, w, *args):
        self._update_lang_cat_from_entry(w, 0)
        self.mark_as_modified()

    def on_entry_lang2_cat_changed(self, w, *args):
        self._update_lang_cat_from_entry(w, 1)
        self.mark_as_modified()

    def on_entry_lang3_cat_changed(self, w, *args):
        self._update_lang_cat_from_entry(w, 2)
        self.mark_as_modified()

    def on_entry_lang4_cat_changed(self, w, *args):
        self._update_lang_cat_from_entry(w, 3)
        self.mark_as_modified()

    def on_entry_lang5_cat_changed(self, w, *args):
        self._update_lang_cat_from_entry(w, 4)
        self.mark_as_modified()

    def on_entry_body_size_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_cb_movement_type_changed(self, w, *args):
        self._update_from_cb(w)
        self.mark_as_modified()

    def on_cb_iq_group_changed(self, w, *args):
        self._update_from_cb(w)
        self.mark_as_modified()

    def on_cb_ability_primary_changed(self, w, *args):
        self._update_from_cb(w)
        self.mark_as_modified()

    def on_cb_ability_secondary_changed(self, w, *args):
        self._update_from_cb(w)
        self.mark_as_modified()

    def on_entry_exp_yield_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_recruit_rate1_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_recruit_rate2_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_base_hp_changed(self, w, *args):
        self._update_from_entry(w)
        if self._level_up_controller is not None:
            self._level_up_controller.queue_render_graph()
            self._render_graph_on_tab_change = True
        self.mark_as_modified()

    def on_entry_weight_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_base_atk_changed(self, w, *args):
        self._update_from_entry(w)
        if self._level_up_controller is not None:
            self._level_up_controller.queue_render_graph()
            self._render_graph_on_tab_change = True
        self.mark_as_modified()

    def on_entry_base_sp_atk_changed(self, w, *args):
        self._update_from_entry(w)
        if self._level_up_controller is not None:
            self._level_up_controller.queue_render_graph()
            self._render_graph_on_tab_change = True
        self.mark_as_modified()

    def on_entry_base_def_changed(self, w, *args):
        self._update_from_entry(w)
        if self._level_up_controller is not None:
            self._level_up_controller.queue_render_graph()
            self._render_graph_on_tab_change = True
        self.mark_as_modified()

    def on_entry_base_sp_def_changed(self, w, *args):
        self._update_from_entry(w)
        if self._level_up_controller is not None:
            self._level_up_controller.queue_render_graph()
            self._render_graph_on_tab_change = True
        self.mark_as_modified()

    def on_entry_size_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_evo_param1_changed(self, w, *args):
        self._update_from_entry(w)
        self._update_param_label()
        self.mark_as_modified()

    def on_cb_evo_param2_changed(self, w, *args):
        self._update_from_cb(w)
        self.mark_as_modified()

    def on_entry_pre_evo_index_changed(self, w, *args):
        self._update_from_entry(w)
        self._update_pre_evo_label()
        self.mark_as_modified()

    def on_cb_evo_method_changed(self, w, *args):
        self._update_from_cb(w)
        self._update_param_label()
        self.mark_as_modified()

    def on_btn_help_evo_params_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("Value depends on Main Requirement:\n"
              "- Never Evolves: Unused\n"
              "- Level: Level required to evolve\n"
              "- IQ: IQ required\n"
              "- Items: ID of the item required\n"
              "- Recruited: ID of the Pokémon you have to recruit\n"
              "- No Main Requirement: Unused"),
            title=_("Evolution Parameters")
        )
        md.run()
        md.destroy()

    def on_btn_help_recruit_rate_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("The values are actually percentages.\n"
              "10 -> 1.0%,\n"
              "100 -> 10.0%,\n"
              "1000 -> 100%, etc.\n\n"
              "If you answered yes to the question asking if you played EoT or EoD in the personality test and you "
              "haven't recruited this Pokémon yet, the second recruit rate is used instead.\n"
              "If you have recruited this Pokémon already, its recruit rate is halved (only if it's positive)."),
            title=_("Recruit Rate")
        )
        md.run()
        md.destroy()

    def on_btn_help_hp_regeneration_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("The % of HP that this Pokémon regenerates at the end of "
              "each turn is equal to 1/(value * 2), before applying any modifiers.\n"
              "The final value is capped between 1/30 and 1/500"),
            title=_("HP Regeneration")
        )
        md.run()
        md.destroy()

    def on_btn_help_can_move_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("Whether or not the enemy or ally AI will move the Pokémon in dungeons."),
            title=_("Can Move?")
        )
        md.run()
        md.destroy()
    
    def on_btn_help_can_throw_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("Whether or not the Pokémon can throw any items."),
            title=_("Can Throw Items?")
        )
        md.run()
        md.destroy()
        
    def on_btn_help_chest_drop_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("""Controls the drop rates of different types of chests.
Each drop type x has a chance of (x rate)/(sum of all the rates) to be selected."""),
            title=_("Chests drop rates")
        )
        md.run()
        md.destroy()
    
    def on_btn_help_can_evolve_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("Whether or not the Pokémon can evolve at Luminous Spring (If it's off, it will never be allowed to "
              "evolve even if it has an evolution)."),
            title=_("Can Evolve?")
        )
        md.run()
        md.destroy()

    def on_btn_help_item_required_for_spawning_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("Whether or not you need to have a special item in the bag (mystery part/secret slab) for "
              "the Pokémon to spawn in dungeons"),
            title=_("Item Required for spawning?")
        )
        md.run()
        md.destroy()

    def on_btn_help_unk21_h_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("If the current $SCENARIO_BALANCE_FLAG value is lower than this number, the pokémon won't spawn in dungeons."),
            title=_("Spawn Threshold")
        )
        md.run()
        md.destroy()

    def on_btn_help_weight_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("Affects the damage the Pokémon takes when attacked with Grass Knot."),
            title=_("Weight")
        )
        md.run()
        md.destroy()

    def on_btn_help_size_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("Affects the damage the Pokémon takes when attacked with a Sizebust Orb."),
            title=_("Size")
        )
        md.run()
        md.destroy()

    def on_entry_exclusive_item1_changed(self, w, *args):
        match = PATTERN.match(w.get_text())
        if match is None:
            return
        try:
            val = int(match.group(1))
        except ValueError:
            return
        setattr(self.entry, 'exclusive_item1', val)
        self.mark_as_modified()

    def on_entry_exclusive_item2_changed(self, w, *args):
        match = PATTERN.match(w.get_text())
        if match is None:
            return
        try:
            val = int(match.group(1))
        except ValueError:
            return
        setattr(self.entry, 'exclusive_item2', val)
        self.mark_as_modified()

    def on_entry_exclusive_item3_changed(self, w, *args):
        match = PATTERN.match(w.get_text())
        if match is None:
            return
        try:
            val = int(match.group(1))
        except ValueError:
            return
        setattr(self.entry, 'exclusive_item3', val)
        self.mark_as_modified()

    def on_entry_exclusive_item4_changed(self, w, *args):
        match = PATTERN.match(w.get_text())
        if match is None:
            return
        try:
            val = int(match.group(1))
        except ValueError:
            return
        setattr(self.entry, 'exclusive_item4', val)
        self.mark_as_modified()

    def on_entry_unk31_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_base_movement_speed_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_unk17_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_unk18_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_cb_shadow_size_changed(self, w, *args):
        self._update_from_cb(w)
        self.mark_as_modified()

    def on_entry_hp_regeneration_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_unk21_h_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_chance_spawn_asleep_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_unk27_changed(self, w, *args):
        self._update_from_entry(w)
        self._update_chance_label()
        self.mark_as_modified()

    def on_entry_unk29_changed(self, w, *args):
        self._update_from_entry(w)
        self._update_chance_label()
        self.mark_as_modified()

    def on_entry_unk28_changed(self, w, *args):
        self._update_from_entry(w)
        self._update_chance_label()
        self.mark_as_modified()

    def on_entry_unk30_changed(self, w, *args):
        self._update_from_entry(w)
        self._update_chance_label()
        self.mark_as_modified()

    def on_entry_base_form_index_changed(self, w, *args):
        self._update_from_entry(w)
        self._update_base_form_label()
        self.mark_as_modified()

    def on_switch_bitfield1_0_state_set(self, w, *args):
        self._update_from_switch(w)
        self.mark_as_modified()

    def on_switch_bitfield1_1_state_set(self, w, *args):
        self._update_from_switch(w)
        self.mark_as_modified()

    def on_switch_bitfield1_2_state_set(self, w, *args):
        self._update_from_switch(w)
        self.mark_as_modified()

    def on_switch_bitfield1_3_state_set(self, w, *args):
        self._update_from_switch(w)
        self.mark_as_modified()

    def on_switch_can_move_state_set(self, w, *args):
        self._update_from_switch(w)
        self.mark_as_modified()

    def on_switch_bitfield1_5_state_set(self, w, *args):
        self._update_from_switch(w)
        self.mark_as_modified()

    def on_switch_can_evolve_state_set(self, w, *args):
        self._update_from_switch(w)
        self.mark_as_modified()

    def on_switch_item_required_for_spawning_state_set(self, w, *args):
        self._update_from_switch(w)
        self.mark_as_modified()

    def on_btn_export_clicked(self, *args):
        dialog: Gtk.Dialog = self.builder.get_object('export_dialog')
        dialog.resize(640, 560)
        dialog.set_attached_to(SkyTempleMainController.window())
        dialog.set_transient_for(SkyTempleMainController.window())

        # Fill Pokémon tree
        store: Gtk.TreeStore = self.builder.get_object('export_dialog_store')
        store.clear()
        monster_entries_by_base_id: Dict[int, List[MdEntry]] = {}
        for entry in self.module.monster_md.entries:
            if entry.md_index_base not in monster_entries_by_base_id:
                monster_entries_by_base_id[entry.md_index_base] = []
            monster_entries_by_base_id[entry.md_index_base].append(entry)

        for baseid, entry_list in monster_entries_by_base_id.items():
            name = self.module.project.get_string_provider().get_value(StringType.POKEMON_NAMES, baseid)
            entry_main_tree = self.module.generate_entry__entity_root(baseid, name)
            ent_root = store.append(None, [
                -1, -1, False, entry_main_tree[0],
                entry_main_tree[1], False, False
            ])

            for entry in entry_list:
                entry_main_tree = self.module.generate_entry__entry(entry.md_index, entry.gender)
                store.append(
                    ent_root, [
                        entry_main_tree[4], -1, True, entry_main_tree[0],
                        entry_main_tree[1], False, False
                    ]
                )

        names, md_gender1, md_gender2, moveset, moveset2, stats, portraits, portraits2 = self.module.get_export_data(self.entry)
        we_are_gender1 = md_gender1 == self.entry

        if md_gender2 is None:
            sw: Gtk.Switch = self.builder.get_object('export_type_other_gender')
            sw.set_active(False)
            sw.set_sensitive(False)

        if portraits is None:
            sw: Gtk.Switch = self.builder.get_object('export_type_portraits_current_gender')
            sw.set_active(False)
            sw.set_sensitive(False)

        if portraits2 is None:
            sw: Gtk.Switch = self.builder.get_object('export_type_portraits_other_gender')
            sw.set_active(False)
            sw.set_sensitive(False)

        if stats is None:
            sw: Gtk.Switch = self.builder.get_object('export_type_stats')
            sw.set_active(False)
            sw.set_sensitive(False)

        if moveset is None:
            sw: Gtk.Switch = self.builder.get_object('export_type_moveset1')
            sw.set_active(False)
            sw.set_sensitive(False)

        if moveset2 is None:
            sw: Gtk.Switch = self.builder.get_object('export_type_moveset2')
            sw.set_active(False)
            sw.set_sensitive(False)

        resp = dialog.run()
        dialog.hide()

        if resp == Gtk.ResponseType.APPLY:
            # Create output XML

            if not self.builder.get_object('export_type_current_gender').get_active():
                if we_are_gender1:
                    md_gender1 = None
                else:
                    md_gender2 = None
            if not self.builder.get_object('export_type_other_gender').get_active():
                if not we_are_gender1:
                    md_gender1 = None
                else:
                    md_gender2 = None
            if not self.builder.get_object('export_type_names').get_active():
                names = None
            if not self.builder.get_object('export_type_stats').get_active():
                stats = None
            if not self.builder.get_object('export_type_moveset1').get_active():
                moveset = None
            if not self.builder.get_object('export_type_moveset2').get_active():
                moveset2 = None
            if not self.builder.get_object('export_type_portraits_current_gender').get_active():
                if we_are_gender1:
                    portraits = None
                else:
                    portraits2 = None
            if not self.builder.get_object('export_type_portraits_other_gender').get_active():
                if not we_are_gender1:
                    portraits = None
                else:
                    portraits2 = None

            xml = monster_xml_export(
                self.module.project.get_rom_module().get_static_data().game_version,
                md_gender1, md_gender2, names, moveset, moveset2, stats, portraits, portraits2
            )

            # 1. Export to file
            if self.builder.get_object('export_file_switch').get_active():
                save_diag = Gtk.FileChooserNative.new(
                    _("Export Pokémon as..."),
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
                                                Gtk.ButtonsType.OK, "Export was canceled.")
                    md.set_position(Gtk.WindowPosition.CENTER)
                    md.run()
                    md.destroy()
                    return

            # 2. Import to selected Pokémon
            selected_monsters: List[int] = []
            def collect_monsters_recurse(titer: Optional[Gtk.TreeIter]):
                for i in range(store.iter_n_children(titer)):
                    child = store.iter_nth_child(titer, i)
                    if store[child][2] and store[child][5]:  # is floor and is selected
                        selected_monsters.append(store[child][0])
                    collect_monsters_recurse(child)

            collect_monsters_recurse(None)
            self.module.import_from_xml(selected_monsters, xml)

    def on_btn_import_clicked(self, *args):
        save_diag = Gtk.FileChooserNative.new(
            _("Import Pokémon from..."),
            SkyTempleMainController.window(),
            Gtk.FileChooserAction.OPEN,
            None, None
        )

        add_dialog_xml_filter(save_diag)
        response = save_diag.run()
        fn = save_diag.get_filename()
        save_diag.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            self.module.import_from_xml([self.entry.md_index], ElementTree.parse(fn).getroot())
            SkyTempleMainController.reload_view()

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

    def _init_language_labels(self):
        langs = self._string_provider.get_languages()
        for lang_id in range(0, 5):
            gui_id = lang_id + 1
            gui_label: Gtk.Label = self.builder.get_object(f'label_lang{gui_id}')
            gui_label_cat: Gtk.Label = self.builder.get_object(f'label_lang{gui_id}_cat')
            gui_entry: Gtk.Entry = self.builder.get_object(f'entry_lang{gui_id}')
            gui_entry_cat: Gtk.Entry = self.builder.get_object(f'entry_lang{gui_id}_cat')
            if lang_id < len(langs):
                # We have this language
                gui_label.set_text(_(langs[lang_id].name_localized) + ':')
                gui_label_cat.set_text(_(langs[lang_id].name_localized) + ':')
            else:
                # We don't.
                gui_label.set_text("")
                gui_entry.set_sensitive(False)
                gui_label_cat.set_text("")
                gui_entry_cat.set_sensitive(False)

    def _init_entid(self):
        self.builder.get_object(f'label_base_id').set_text(f'#{self.entry.md_index_base:03}')
        name = self._string_provider.get_value(StringType.POKEMON_NAMES, self.entry.md_index_base)
        self.builder.get_object('label_id_name').set_text(f'${self.entry.md_index:04d}: {name}')

    def _init_stores(self):
        # Genders
        self._comboxbox_for_enum(['cb_gender'], Gender)
        # Types
        self._comboxbox_for_enum(['cb_type_primary', 'cb_type_secondary'], PokeType)
        # Movement Types
        self._comboxbox_for_enum(['cb_movement_type'], MovementType)
        # IQ Groups
        self._comboxbox_for_enum(['cb_iq_group'], IQGroup)
        # Abilities
        self._comboxbox_for_enum(['cb_ability_primary', 'cb_ability_secondary'], Ability, True)
        # Evolution Methods
        self._comboxbox_for_enum(['cb_evo_method'], EvolutionMethod)
        # Additional Requirement
        self._comboxbox_for_enum(['cb_evo_param2'], AdditionalRequirement)
        
        # Shadow Size
        self._comboxbox_for_enum(['cb_shadow_size'], ShadowSize)

    def _init_values(self):
        # Names
        langs = self._string_provider.get_languages()
        for lang_id in range(0, 5):
            gui_id = lang_id + 1
            gui_entry: Gtk.Entry = self.builder.get_object(f'entry_lang{gui_id}')
            gui_entry_cat: Gtk.Entry = self.builder.get_object(f'entry_lang{gui_id}_cat')
            if lang_id < len(langs):
                # We have this language
                gui_entry.set_text(self._string_provider.get_value(StringType.POKEMON_NAMES,
                                                                   self.entry.md_index_base,
                                                                   langs[lang_id]))
                gui_entry_cat.set_text(self._string_provider.get_value(StringType.POKEMON_CATEGORIES,
                                                                       self.entry.md_index_base,
                                                                       langs[lang_id]))

        # Stats
        self._set_entry('entry_personality', self.module.get_personality(self.item_id))
        self._set_entry('entry_unk31', self.entry.unk31)
        self._set_entry('entry_national_pokedex_number', self.entry.national_pokedex_number)
        self._set_entry('entry_entid', self.entry.entid)
        self._set_entry('entry_sprite_index', self.entry.sprite_index)
        self._set_entry('entry_base_movement_speed', self.entry.base_movement_speed)
        self._set_entry('entry_pre_evo_index', self.entry.pre_evo_index)
        self._set_entry('entry_base_form_index', self.entry.base_form_index)
        self._set_cb('cb_evo_method', self.entry.evo_method.value)
        self._set_entry('entry_evo_param1', self.entry.evo_param1)
        self._set_cb('cb_evo_param2', self.entry.evo_param2.value)
        self._set_cb('cb_gender', self.entry.gender.value)
        self._set_entry('entry_body_size', self.entry.body_size)
        self._set_cb('cb_type_primary', self.entry.type_primary.value)
        self._set_cb('cb_type_secondary', self.entry.type_secondary.value)
        self._set_cb('cb_movement_type', self.entry.movement_type.value)
        self._set_cb('cb_iq_group', self.entry.iq_group.value)
        self._set_cb('cb_ability_primary', self.entry.ability_primary.value)
        self._set_cb('cb_ability_secondary', self.entry.ability_secondary.value)
        self._set_switch('switch_bitfield1_0', self.entry.bitfield1_0)
        self._set_switch('switch_bitfield1_1', self.entry.bitfield1_1)
        self._set_switch('switch_bitfield1_2', self.entry.bitfield1_2)
        self._set_switch('switch_bitfield1_3', self.entry.bitfield1_3)
        self._set_switch('switch_can_move', self.entry.can_move)
        self._set_switch('switch_bitfield1_5', self.entry.bitfield1_5)
        self._set_switch('switch_can_evolve', self.entry.can_evolve)
        self._set_switch('switch_item_required_for_spawning', self.entry.item_required_for_spawning)
        self._set_entry('entry_exp_yield', self.entry.exp_yield)
        self._set_entry('entry_recruit_rate1', self.entry.recruit_rate1)
        self._set_entry('entry_base_hp', self.entry.base_hp)
        self._set_entry('entry_recruit_rate2', self.entry.recruit_rate2)
        self._set_entry('entry_base_atk', self.entry.base_atk)
        self._set_entry('entry_base_sp_atk', self.entry.base_sp_atk)
        self._set_entry('entry_base_def', self.entry.base_def)
        self._set_entry('entry_base_sp_def', self.entry.base_sp_def)
        self._set_entry('entry_weight', self.entry.weight)
        self._set_entry('entry_size', self.entry.size)
        self._set_entry('entry_unk17', self.entry.unk17)
        self._set_entry('entry_unk18', self.entry.unk18)
        self._set_cb('cb_shadow_size', self.entry.shadow_size.value)
        self._set_entry('entry_chance_spawn_asleep', self.entry.chance_spawn_asleep)
        self._set_entry('entry_hp_regeneration', self.entry.hp_regeneration)
        self._set_entry('entry_unk21_h', self.entry.unk21_h)
        self._set_entry('entry_exclusive_item1', self.item_names[self.entry.exclusive_item1])
        self._set_entry('entry_exclusive_item2', self.item_names[self.entry.exclusive_item2])
        self._set_entry('entry_exclusive_item3', self.item_names[self.entry.exclusive_item3])
        self._set_entry('entry_exclusive_item4', self.item_names[self.entry.exclusive_item4])
        self._set_entry('entry_unk27', self.entry.unk27)
        self._set_entry('entry_unk28', self.entry.unk28)
        self._set_entry('entry_unk29', self.entry.unk29)
        self._set_entry('entry_unk30', self.entry.unk30)

    def mark_as_modified(self):
        if not self._is_loading:
            self.module.mark_md_as_modified(self.item_id)

    def _comboxbox_for_enum(self, names: List[str], enum: Type[Enum], sort_by_name = False):
        store = Gtk.ListStore(int, str)  # id, name
        if sort_by_name:
            enum = sorted(enum, key=lambda x:self._enum_entry_to_str(x))
        for entry in enum:
            store.append([entry.value, self._enum_entry_to_str(entry)])
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
        cb: Gtk.ComboBox = self.builder.get_object(cb_name)
        l_iter: Gtk.TreeIter = cb.get_model().get_iter_first()
        while l_iter:
            row = cb.get_model()[l_iter]
            if row[0] == value:
                cb.set_active_iter(l_iter)
                return
            l_iter = cb.get_model().iter_next(l_iter)

    def _set_switch(self, switch_name, value):
        self.builder.get_object(switch_name).set_active(value)

    def _update_from_entry(self, w: Gtk.Entry):
        attr_name = Gtk.Buildable.get_name(w)[6:]
        try:
            val = int(w.get_text())
        except ValueError:
            return
        setattr(self.entry, attr_name, val)

    def _update_from_switch(self, w: Gtk.Entry):
        attr_name = Gtk.Buildable.get_name(w)[7:]
        setattr(self.entry, attr_name, w.get_active())

    def _update_from_cb(self, w: Gtk.ComboBox):
        attr_name = Gtk.Buildable.get_name(w)[3:]
        val = w.get_model()[w.get_active_iter()][0]
        current_val = getattr(self.entry, attr_name)
        if isinstance(current_val, Enum):
            enum_class = current_val.__class__
            val = enum_class(val)
        setattr(self.entry, attr_name, val)

    def _update_lang_from_entry(self, w: Gtk.Entry, lang_index):
        lang = self._string_provider.get_languages()[lang_index]
        self._string_provider.get_model(lang).strings[
            self._string_provider.get_index(StringType.POKEMON_NAMES, self.entry.md_index_base)
        ] = w.get_text()

    def _update_lang_cat_from_entry(self, w: Gtk.Entry, lang_index):
        lang = self._string_provider.get_languages()[lang_index]
        self._string_provider.get_model(lang).strings[
            self._string_provider.get_index(StringType.POKEMON_CATEGORIES, self.entry.md_index_base)
        ] = w.get_text()

    def _init_sub_pages(self):
        notebook: Gtk.Notebook = self.builder.get_object('main_notebook')
        tab_label: Gtk.Label = Gtk.Label.new(_('Stats and Moves'))
        level_up_view, self._level_up_controller = self.module.get_level_up_view(self.item_id)
        notebook.append_page(level_up_view, tab_label)
        tab_label: Gtk.Label = Gtk.Label.new(_('Portraits'))
        notebook.append_page(self.module.get_portrait_view(self.item_id), tab_label)
        self._reload_sprite_page()

    def _reload_sprite_page(self):
        notebook: Gtk.Notebook = self.builder.get_object('main_notebook')
        if self._cached_sprite_page:
            notebook.remove_page(self._cached_sprite_page)
        tab_label: Gtk.Label = Gtk.Label.new(_('Sprites'))
        tab_label.show()
        self._cached_sprite_page = notebook.append_page(
            self.module.get_sprite_view(self.entry.sprite_index, self.item_id), tab_label
        )

    def _update_param_label(self):
        label: Gtk.Label = self.builder.get_object('label_param')
        entry: Gtk.Entry = self.builder.get_object('entry_evo_param1')
        cb: Gtk.ComboBox = self.builder.get_object('cb_evo_method')
        val = cb.get_model()[cb.get_active_iter()][0]
        try:
            entry_id = int(entry.get_text())
            if val==3:
                if entry_id >= MAX_ITEMS:
                    raise ValueError()
                name = self._string_provider.get_value(StringType.ITEM_NAMES, entry_id)
                label.set_text(f'#{entry_id:03d}: {name}')
            elif val==4:
                if entry_id > NUM_ENTITIES:
                    raise ValueError()
                entry = self.module.monster_md[entry_id]
                name = self._string_provider.get_value(StringType.POKEMON_NAMES, entry.md_index_base)
                label.set_text(f'#{entry.md_index_base:03d}: {name}')
            else:
                label.set_text(f'')
        except BaseException:
            label.set_text(_('??? Enter a valid parameter (#)'))
        
    def _update_base_form_label(self):
        label: Gtk.Label = self.builder.get_object('label_base_form_index')
        entry: Gtk.Entry = self.builder.get_object('entry_base_form_index')
        try:
            entry_id = int(entry.get_text())
            if entry_id > NUM_ENTITIES:
                raise ValueError()
            entry = self.module.monster_md[entry_id]
            name = self._string_provider.get_value(StringType.POKEMON_NAMES, entry.md_index_base)
            label.set_text(f'#{entry.md_index_base:03d}: {name}')
        except BaseException:
            label.set_text(_('??? Enter a valid Base ID (#)'))

    def _update_pre_evo_label(self):
        label: Gtk.Label = self.builder.get_object('label_pre_evo_index')
        entry: Gtk.Entry = self.builder.get_object('entry_pre_evo_index')
        try:
            entry_id = int(entry.get_text())
            entry = self.module.monster_md[entry_id]
            name = self._string_provider.get_value(StringType.POKEMON_NAMES, entry.md_index_base)
            label.set_text(f'${entry.md_index:04d}: {name} ({entry.gender.name[0]})')
        except BaseException:
            label.set_text(_('??? Enter a valid Entry ID ($)'))
    
    def _update_chance_label(self):
        label1: Gtk.Label = self.builder.get_object('label_chance_no_drop')
        entry1: Gtk.Entry = self.builder.get_object('entry_unk27')
        label2: Gtk.Label = self.builder.get_object('label_chance_normal_items')
        entry2: Gtk.Entry = self.builder.get_object('entry_unk28')
        label3: Gtk.Label = self.builder.get_object('label_chance_exclusive1')
        entry3: Gtk.Entry = self.builder.get_object('entry_unk29')
        label4: Gtk.Label = self.builder.get_object('label_chance_exclusive2')
        entry4: Gtk.Entry = self.builder.get_object('entry_unk30')
        try:
            entry1_value = int(entry1.get_text())
            if entry1_value==0:
                entry1_value = 1
                entry2_value = entry3_value = entry4_value = 0
            else:
                entry2_value = int(entry2.get_text())
                entry3_value = int(entry3.get_text())
                entry4_value = int(entry4.get_text())
            sum_values = entry1_value+entry2_value+entry3_value+entry4_value
            label1.set_text(f'{entry1_value/sum_values*100:2.02f}%')
            label2.set_text(f'{entry2_value/sum_values*100:2.02f}%')
            label3.set_text(f'{entry3_value/sum_values*100:2.02f}%')
            label4.set_text(f'{entry4_value/sum_values*100:2.02f}%')
        except BaseException:
            label1.set_text(_('???'))
            label2.set_text(_('???'))
            label3.set_text(_('???'))
            label4.set_text(_('???'))

    def _check_sprite_size(self, show_warning):
        """
        Check that the data in the unknown Pokémon sprite-related metadata
        table matches the currently selected sprite of the Pokémon. If not, change
        the value and save it.
        """
        try:
            if self.entry.sprite_index < 0:
                return
            with self._monster_bin as sprites:
                sprite_bin = sprites[self.entry.sprite_index]
                sprite = FileType.WAN.deserialize(FileType.COMMON_AT.deserialize(sprite_bin).decompress())
            sprite_size_table = self.module.get_pokemon_sprite_data_table()
            check_value = sprite_size_table[self.entry.md_index_base].sprite_tile_slots
            max_tile_slots_needed = max(
                (f.unk2 & 0x3FF) + math.ceil(f.resolution.x * f.resolution.y / 256)
                for f in sprite.model.meta_frame_store.meta_frames
            )
            # There isn't those 2 blocks buffer! Doing this would cause some problems in the long term.
            # Also, this should use the Unk#6 field in the animation info block (see psy's docs about wan files)
            # instead of the calculation above, as it's exactly the result of that
            max_tile_slots_needed = max((6, max_tile_slots_needed))
            if check_value != max_tile_slots_needed:
                sprite_size_table[self.entry.md_index_base].sprite_tile_slots = max_tile_slots_needed
                self.module.set_pokemon_sprite_data_table(sprite_size_table)

                if show_warning:
                    md = SkyTempleMessageDialog(MainController.window(),
                                                Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.WARNING,
                                                Gtk.ButtonsType.OK,
                                                _("The sprite memory size of this Pokémon was too low "
                                                  "for this Pokémon's assigned sprite.\n"
                                                  "SkyTemple automatically corrected it."))
                    md.set_position(Gtk.WindowPosition.CENTER)
                    md.run()
                    md.destroy()

                self.mark_as_modified()
        except BaseException as ex:
            logger.error("Failed to check Pokémon sprite size.", exc_info=ex)
