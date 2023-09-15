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
import logging
import re
import sys
import typing
from enum import Enum
from typing import TYPE_CHECKING, Type, List, Optional, Dict, cast
from xml.etree import ElementTree

import cairo
from explorerscript.util import open_utf8
from gi.repository import Gtk, GLib
from range_typed_integers import u16, u16_checked, u8, u8_checked, i16, i16_checked, i8, i8_checked
from skytemple_files.common.sprite_util import check_and_correct_monster_sprite_size

from skytemple.core.error_handler import display_error
from skytemple.controller.main import MainController
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.module_controller import AbstractController
from skytemple.core.string_provider import StringType
from skytemple.core.ui_utils import add_dialog_xml_filter, catch_overflow, builder_get_assert, assert_not_none, \
    iter_tree_model
from skytemple.module.monster.controller.level_up import LevelUpController
from skytemple.module.portrait.portrait_provider import IMG_DIM
from skytemple_files.common.types.file_types import FileType
from skytemple_files.common.util import add_extension_if_missing, MONSTER_BIN
from skytemple_files.common.xml_util import prettify
from skytemple_files.data.md.protocol import Gender, PokeType, MovementType, IQGroup, Ability, EvolutionMethod, \
    AdditionalRequirement, ShadowSize, MdEntryProtocol
from skytemple.controller.main import MainController as SkyTempleMainController
from skytemple_files.data.monster_xml import monster_xml_export
from skytemple_files.hardcoded.monster_sprite_data_table import IdleAnimType
from skytemple_files.common.i18n_util import f, _

if TYPE_CHECKING:
    from skytemple.module.monster.module import MonsterModule
MAX_ITEMS = 1400
PATTERN = re.compile(r'.*\(#(\d+)\).*')
logger = logging.getLogger(__name__)
MAX_EVOS = 8
MAX_EGGS = 6


class MonsterController(AbstractController):
    _last_open_tab_id = 0
    _previous_item_id = -1

    def __init__(self, module: 'MonsterModule', item_id: int):
        self.module = module
        self.item_id = item_id
        self.entry: MdEntryProtocol = self.module.get_entry(self.item_id)

        self._monster_bin = self.module.project.open_file_in_rom(MONSTER_BIN, FileType.BIN_PACK, threadsafe=True)

        self.builder: Gtk.Builder = None  # type: ignore
        self._is_loading = False
        self._string_provider = module.project.get_string_provider()
        self._sprite_provider = module.project.get_sprite_provider()
        self._portrait_provider = module.project.get_module('portrait').get_portrait_provider()
        self._level_up_controller: Optional[LevelUpController] = None
        self._cached_sprite_page: Optional[int] = None

        self._render_graph_on_tab_change = True

        self.item_names = {}
        for i in range(0, MAX_ITEMS):
            name = self.module.project.get_string_provider().get_value(StringType.ITEM_NAMES, i)
            self.item_names[i] = f'{name} (#{i:04})'

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'monster.glade')
        assert self.builder

        self._sprite_provider.reset()
        self._portrait_provider.reset()

        self._init_language_labels()
        self._init_entid()
        self._init_stores()
        self._init_sub_pages()

        # Init Items Completion
        store = builder_get_assert(self.builder, Gtk.ListStore, 'store_completion_items')

        for item in self.item_names.values():
            store.append([item])

        self._is_loading = True
        self._init_values()
        self._is_loading = False

        self._update_pre_evo_label()
        self._update_base_form_label()
        self._update_param_label()
        self._update_chance_label()

        if self.module.project.is_patch_applied("ExpandPokeList"):
            builder_get_assert(self.builder, Gtk.Label, 'lbl_unk_1_0').set_text(_("Spinda Egg"))
            builder_get_assert(self.builder, Gtk.Label, 'lbl_unk_1_1').set_text(_("Spinda Recruit"))
            builder_get_assert(self.builder, Gtk.Label, 'lbl_unk_1_2').set_text(_("Don't appear in Missions"))
            builder_get_assert(self.builder, Gtk.Label, 'lbl_unk_1_3').set_text(_("Don't appear in Missions during story"))
            builder_get_assert(self.builder, Gtk.Label, 'lbl_unk_17').set_text(_("Sprite Size"))
            builder_get_assert(self.builder, Gtk.Label, 'lbl_unk_18').set_text(_("Sprite File Size"))

        self._ent_names: Dict[int, str] = {}

        self._init_monster_store()

        stack = builder_get_assert(self.builder, Gtk.Stack, 'evo_stack')
        if self.module.has_md_evo():
            self._md_evo = self.module.get_md_evo()
            self._init_evo_lists()
            stack.set_visible_child(builder_get_assert(self.builder, Gtk.Widget, 'box_evo'))
        else:
            self._md_evo = None
            stack.set_visible_child(builder_get_assert(self.builder, Gtk.Widget, 'box_no_evo'))

        self.builder.connect_signals(self)
        builder_get_assert(self.builder, Gtk.DrawingArea, 'draw_sprite').queue_draw()

        notebook = builder_get_assert(self.builder, Gtk.Notebook, 'main_notebook')
        notebook.set_current_page(self.__class__._last_open_tab_id)

        self._check_sprite_size(self.__class__._previous_item_id != self.item_id)
        self.__class__._previous_item_id = self.item_id

        return builder_get_assert(self.builder, Gtk.Widget, 'box_main_parent')

    @typing.no_type_check
    def unload(self):
        # We need to destroy this first.
        # GTK is an enigma sometimes.
        builder_get_assert(self.builder, Gtk.Widget, 'export_dialog').destroy()
        super().unload()
        self.module = None
        self.item_id = None
        self.entry = None

        self._monster_bin = None

        self.builder = None
        self._is_loading = False
        self._string_provider = None
        self._sprite_provider = None
        self._portrait_provider = None
        self._level_up_controller = None
        self._cached_sprite_page = None
        self._render_graph_on_tab_change = True
        self.item_names = {}

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

    @catch_overflow(u16)
    def on_entry_national_pokedex_number_changed(self, w, *args):
        try:
            val = u16_checked(int(w.get_text()))
        except ValueError:
            return
        self.entry.national_pokedex_number = val
        self.mark_as_modified()

    @catch_overflow(u16)
    def on_entry_entid_changed(self, w, *args):
        try:
            val = u16_checked(int(w.get_text()))
        except ValueError:
            return
        self.entry.entid = val
        self.mark_as_modified()

    @catch_overflow(u8)
    def on_entry_personality_changed(self, w, *args):
        try:
            self.module.set_personality(self.item_id, u8_checked(int(w.get_text())))
        except ValueError:
            pass

    def on_cb_idle_anim_changed(self, w, *args):
        try:
            val = w.get_model()[w.get_active_iter()][0]
            self.module.set_idle_anim_type(
                self.item_id,
                IdleAnimType(val)  # type: ignore
            )
        except ValueError:
            pass

    @catch_overflow(i16)
    def on_entry_sprite_index_changed(self, w, *args):
        try:
            val = i16_checked(int(w.get_text()))
        except ValueError:
            return
        self.entry.sprite_index = val
        self.mark_as_modified()
        self._sprite_provider.reset()
        self._check_sprite_size(False)
        builder_get_assert(self.builder, Gtk.DrawingArea, 'draw_sprite').queue_draw()
        self._reload_sprite_page()

    def on_cb_gender_changed(self, w, *args):
        self._update_from_cb(w)
        # Changing the gender should also refresh the tree, as the gender is marked here.
        self.module.refresh(self.item_id)
        self.mark_as_modified()

    def on_entry_lang1_changed(self, w, *args):
        builder_get_assert(self.builder, Gtk.Label, 'label_id_name').set_text(f'${self.entry.md_index:04d}: {w.get_text()}')
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

    @catch_overflow(u8)
    def on_entry_body_size_changed(self, w, *args):
        try:
            val = u8_checked(int(w.get_text()))
        except ValueError:
            return
        self.entry.body_size = val
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

    @catch_overflow(u16)
    def on_entry_exp_yield_changed(self, w, *args):
        try:
            val = u16_checked(int(w.get_text()))
        except ValueError:
            return
        self.entry.exp_yield = val
        self.mark_as_modified()

    @catch_overflow(i16)
    def on_entry_recruit_rate1_changed(self, w, *args):
        try:
            val = i16_checked(int(w.get_text()))
        except ValueError:
            return
        self.entry.recruit_rate1 = val
        self.mark_as_modified()

    @catch_overflow(i16)
    def on_entry_recruit_rate2_changed(self, w, *args):
        try:
            val = i16_checked(int(w.get_text()))
        except ValueError:
            return
        self.entry.recruit_rate2 = val
        self.mark_as_modified()

    @catch_overflow(u16)
    def on_entry_base_hp_changed(self, w, *args):
        try:
            val = u16_checked(int(w.get_text()))
        except ValueError:
            return
        self.entry.base_hp = val
        if self._level_up_controller is not None:
            self._level_up_controller.queue_render_graph()
            self._render_graph_on_tab_change = True
        self.mark_as_modified()

    @catch_overflow(i16)
    def on_entry_weight_changed(self, w, *args):
        try:
            val = i16_checked(int(w.get_text()))
        except ValueError:
            return
        self.entry.weight = val
        self.mark_as_modified()

    @catch_overflow(u8)
    def on_entry_base_atk_changed(self, w, *args):
        try:
            val = u8_checked(int(w.get_text()))
        except ValueError:
            return
        self.entry.base_atk = val
        if self._level_up_controller is not None:
            self._level_up_controller.queue_render_graph()
            self._render_graph_on_tab_change = True
        self.mark_as_modified()

    @catch_overflow(u8)
    def on_entry_base_sp_atk_changed(self, w, *args):
        try:
            val = u8_checked(int(w.get_text()))
        except ValueError:
            return
        self.entry.base_sp_atk = val
        if self._level_up_controller is not None:
            self._level_up_controller.queue_render_graph()
            self._render_graph_on_tab_change = True
        self.mark_as_modified()

    @catch_overflow(u8)
    def on_entry_base_def_changed(self, w, *args):
        try:
            val = u8_checked(int(w.get_text()))
        except ValueError:
            return
        self.entry.base_def = val
        if self._level_up_controller is not None:
            self._level_up_controller.queue_render_graph()
            self._render_graph_on_tab_change = True
        self.mark_as_modified()

    @catch_overflow(u8)
    def on_entry_base_sp_def_changed(self, w, *args):
        try:
            val = u8_checked(int(w.get_text()))
        except ValueError:
            return
        self.entry.base_sp_def = val
        if self._level_up_controller is not None:
            self._level_up_controller.queue_render_graph()
            self._render_graph_on_tab_change = True
        self.mark_as_modified()

    @catch_overflow(i16)
    def on_entry_size_changed(self, w, *args):
        try:
            val = i16_checked(int(w.get_text()))
        except ValueError:
            return
        self.entry.size = val
        self.mark_as_modified()

    @catch_overflow(u16)
    def on_entry_evo_param1_changed(self, w, *args):
        try:
            val = u16_checked(int(w.get_text()))
        except ValueError:
            return
        self.entry.evo_param1 = val
        self._update_param_label()
        self.mark_as_modified()

    def on_cb_evo_param2_changed(self, w, *args):
        self._update_from_cb(w)
        self.mark_as_modified()

    @catch_overflow(u16)
    def on_entry_pre_evo_index_changed(self, w, *args):
        try:
            val = u16_checked(int(w.get_text()))
        except ValueError:
            return
        self.entry.pre_evo_index = val
        self._update_pre_evo_label()
        self.mark_as_modified()

    def on_cb_evo_method_changed(self, w, *args):
        self._update_from_cb(w)
        self._update_param_label()
        self.mark_as_modified()

    def on_btn_help_idle_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("This value can only be edited with the ChangePokemonGroundAnim patch. \n"
              "This tells how idle animations should be handled for each pokemon. "),
            title=_("Idle Animation Types")
        )
        md.run()
        md.destroy()

    def on_btn_help_evo_params_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("Value depends on Main Requirement:\n"
              "- Not an Evolved Form: Unused\n"
              "- Level: Level required to evolve\n"
              "- IQ: IQ required\n"
              "- Items: ID of the item required\n"
              "- Recruited: ID of the Pokémon you have to recruit\n"
              "- No Main Requirement: Unused"),
            title=_("Evolution Parameters")
        )
        md.run()
        md.destroy()

    def on_btn_help_base_form_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("This value indicates the family of a pokemon.\n"
              "This is used by a certain type of exclusive items that benefits to a family."),
            title=_("Base Form Info")
        )
        md.run()
        md.destroy()

    def on_btn_help_pre_evo_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("This value indicates the previous evolution of the pokémon.\n"
              "The game use this in several cases: \n"
              "1 - For evolution purposes.\n"
              "2 - When remembering moves at Electivire's shop, you can also remember moves from you pre evolutions up to 2 generations.\n"
              "3 - For missions with an egg as a reward, the egg contains a random Pokémon that is selected among the child Pokémon of the ones in the spawn list of the mission floor.\n"
              "Child Pokémon are computed using the pre evolution value and going recursively until one pokémon without a pre evolution is found.\n"
              "If the ChangeEvoSystem patch is applied, only point 2 applies, the other points are handled with other data."),
            title=_("Pre Evolution Info")
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

    @catch_overflow(i16)
    def on_entry_exclusive_item1_changed(self, w, *args):
        match = PATTERN.match(w.get_text())
        if match is None:
            return
        try:
            val = i16_checked(int(match.group(1)))
        except ValueError:
            return
        self.entry.exclusive_item1 = val
        self.mark_as_modified()

    @catch_overflow(i16)
    def on_entry_exclusive_item2_changed(self, w, *args):
        match = PATTERN.match(w.get_text())
        if match is None:
            return
        try:
            val = i16_checked(int(match.group(1)))
        except ValueError:
            return
        self.entry.exclusive_item2 = val
        self.mark_as_modified()

    @catch_overflow(i16)
    def on_entry_exclusive_item3_changed(self, w, *args):
        match = PATTERN.match(w.get_text())
        if match is None:
            return
        try:
            val = i16_checked(int(match.group(1)))
        except ValueError:
            return
        self.entry.exclusive_item3 = val
        self.mark_as_modified()

    @catch_overflow(i16)
    def on_entry_exclusive_item4_changed(self, w, *args):
        match = PATTERN.match(w.get_text())
        if match is None:
            return
        try:
            val = i16_checked(int(match.group(1)))
        except ValueError:
            return
        self.entry.exclusive_item4 = val
        self.mark_as_modified()

    @catch_overflow(u16)
    def on_entry_unk31_changed(self, w, *args):
        try:
            val = u16_checked(int(w.get_text()))
        except ValueError:
            return
        self.entry.unk31 = val
        self.mark_as_modified()

    @catch_overflow(u16)
    def on_entry_base_movement_speed_changed(self, w, *args):
        try:
            val = u16_checked(int(w.get_text()))
        except ValueError:
            return
        self.entry.base_movement_speed = val
        self.mark_as_modified()

    @catch_overflow(u8)
    def on_entry_unk17_changed(self, w, *args):
        try:
            val = u8_checked(int(w.get_text()))
        except ValueError:
            return
        self.entry.unk17 = val
        self.mark_as_modified()

    @catch_overflow(u8)
    def on_entry_unk18_changed(self, w, *args):
        try:
            val = u8_checked(int(w.get_text()))
        except ValueError:
            return
        self.entry.unk18 = val
        self.mark_as_modified()

    def on_cb_shadow_size_changed(self, w, *args):
        self._update_from_cb(w)
        self.mark_as_modified()

    @catch_overflow(u8)
    def on_entry_hp_regeneration_changed(self, w, *args):
        try:
            val = u8_checked(int(w.get_text()))
        except ValueError:
            return
        self.entry.hp_regeneration = val
        self.mark_as_modified()

    @catch_overflow(i8)
    def on_entry_unk21_h_changed(self, w, *args):
        try:
            val = i8_checked(int(w.get_text()))
        except ValueError:
            return
        self.entry.unk21_h = val
        self.mark_as_modified()

    @catch_overflow(i8)
    def on_entry_chance_spawn_asleep_changed(self, w, *args):
        try:
            val = i8_checked(int(w.get_text()))
        except ValueError:
            return
        self.entry.chance_spawn_asleep = val
        self.mark_as_modified()

    @catch_overflow(i16)
    def on_entry_unk27_changed(self, w, *args):
        try:
            val = i16_checked(int(w.get_text()))
        except ValueError:
            return
        self.entry.unk27 = val
        self._update_chance_label()
        self.mark_as_modified()

    @catch_overflow(i16)
    def on_entry_unk29_changed(self, w, *args):
        try:
            val = i16_checked(int(w.get_text()))
        except ValueError:
            return
        self.entry.unk29 = val
        self._update_chance_label()
        self.mark_as_modified()

    @catch_overflow(i16)
    def on_entry_unk28_changed(self, w, *args):
        try:
            val = i16_checked(int(w.get_text()))
        except ValueError:
            return
        self.entry.unk28 = val
        self._update_chance_label()
        self.mark_as_modified()

    @catch_overflow(i16)
    def on_entry_unk30_changed(self, w, *args):
        try:
            val = i16_checked(int(w.get_text()))
        except ValueError:
            return
        self.entry.unk30 = val
        self._update_chance_label()
        self.mark_as_modified()

    @catch_overflow(i16)
    def on_entry_base_form_index_changed(self, w, *args):
        try:
            val = i16_checked(int(w.get_text()))
        except ValueError:
            return
        self.entry.base_form_index = val
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
        dialog = builder_get_assert(self.builder, Gtk.Dialog, 'export_dialog')
        dialog.resize(640, 560)
        dialog.set_attached_to(SkyTempleMainController.window())
        dialog.set_transient_for(SkyTempleMainController.window())

        # Fill Pokémon tree
        store = builder_get_assert(self.builder, Gtk.TreeStore, 'export_dialog_store')
        store.clear()
        monster_entries_by_base_id: Dict[int, List[MdEntryProtocol]] = {}
        for entry in self.module.monster_md.entries:
            if getattr(entry, self.module.effective_base_attr) not in monster_entries_by_base_id:
                monster_entries_by_base_id[getattr(entry, self.module.effective_base_attr)] = []
            monster_entries_by_base_id[getattr(entry, self.module.effective_base_attr)].append(entry)

        for baseid, entry_list in monster_entries_by_base_id.items():
            name = self.module.project.get_string_provider().get_value(StringType.POKEMON_NAMES, baseid)
            entry_main_tree = self.module.generate_entry__entity_root(baseid, name)
            ent_root = store.append(None, [
                -1, -1, False, entry_main_tree.icon,
                entry_main_tree.name, False, False
            ])

            for entry in entry_list:
                entry_main_tree = self.module.generate_entry__entry(entry.md_index, Gender(entry.gender))  # type: ignore
                store.append(
                    ent_root, [
                        entry_main_tree.item_data, -1, True, entry_main_tree.icon,
                        entry_main_tree.name, False, False
                    ]
                )

        names, md_gender1, md_gender2, moveset, moveset2, stats, portraits, portraits2, personality1, personality2, idle_anim1, idle_anim2 = self.module.get_export_data(
            self.entry)
        we_are_gender1 = md_gender1 == self.entry

        if self.module.project.is_patch_applied('ExpandPokeList'):
            # We do not support multi gender export for now with this patch, too many edge cases.
            md_gender2 = None
            portraits2 = None
            personality2 = None
            idle_anim2 = None

        sw: Gtk.Switch
        if md_gender2 is None:
            sw = builder_get_assert(self.builder, Gtk.Switch, 'export_type_other_gender')
            sw.set_active(False)
            sw.set_sensitive(False)

        if portraits is None:
            sw = builder_get_assert(self.builder, Gtk.Switch, 'export_type_portraits_current_gender')
            sw.set_active(False)
            sw.set_sensitive(False)

        if portraits2 is None:
            sw = builder_get_assert(self.builder, Gtk.Switch, 'export_type_portraits_other_gender')
            sw.set_active(False)
            sw.set_sensitive(False)

        if stats is None:
            sw = builder_get_assert(self.builder, Gtk.Switch, 'export_type_stats')
            sw.set_active(False)
            sw.set_sensitive(False)

        if moveset is None:
            sw = builder_get_assert(self.builder, Gtk.Switch, 'export_type_moveset1')
            sw.set_active(False)
            sw.set_sensitive(False)

        if moveset2 is None:
            sw = builder_get_assert(self.builder, Gtk.Switch, 'export_type_moveset2')
            sw.set_active(False)
            sw.set_sensitive(False)

        resp = dialog.run()
        dialog.hide()

        if resp == Gtk.ResponseType.APPLY:
            # Create output XML

            if not builder_get_assert(self.builder, Gtk.Switch, 'export_type_current_gender').get_active():
                if we_are_gender1:
                    md_gender1 = None
                else:
                    md_gender2 = None
            if not builder_get_assert(self.builder, Gtk.Switch, 'export_type_other_gender').get_active():
                if not we_are_gender1:
                    md_gender1 = None
                else:
                    md_gender2 = None
            if not builder_get_assert(self.builder, Gtk.Switch, 'export_type_names').get_active():
                names = None
            if not builder_get_assert(self.builder, Gtk.Switch, 'export_type_stats').get_active():
                stats = None
            if not builder_get_assert(self.builder, Gtk.Switch, 'export_type_moveset1').get_active():
                moveset = None
            if not builder_get_assert(self.builder, Gtk.Switch, 'export_type_moveset2').get_active():
                moveset2 = None
            if not builder_get_assert(self.builder, Gtk.Switch, 'export_type_portraits_current_gender').get_active():
                if we_are_gender1:
                    portraits = None
                else:
                    portraits2 = None
            if not builder_get_assert(self.builder, Gtk.Switch, 'export_type_portraits_other_gender').get_active():
                if not we_are_gender1:
                    portraits = None
                else:
                    portraits2 = None

            xml = monster_xml_export(
                self.module.project.get_rom_module().get_static_data().game_version,
                md_gender1, md_gender2, names, moveset, moveset2, stats, portraits, portraits2,
                personality1, personality2, idle_anim1, idle_anim2
            )

            # 1. Export to file
            if builder_get_assert(self.builder, Gtk.Switch, 'export_file_switch').get_active():
                save_diag = Gtk.FileChooserNative.new(
                    _("Export Pokémon as..."),
                    SkyTempleMainController.window(),
                    Gtk.FileChooserAction.SAVE,
                    None, None
                )

                add_dialog_xml_filter(save_diag)
                response = save_diag.run()
                fn = save_diag.get_filename()
                save_diag.destroy()

                if response == Gtk.ResponseType.ACCEPT and fn is not None:
                    fn = add_extension_if_missing(fn, 'xml')
                    with open_utf8(fn, 'w') as f:
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
                    if child is not None:
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

        if response == Gtk.ResponseType.ACCEPT and fn is not None:
            self.module.import_from_xml([self.entry.md_index], ElementTree.parse(fn).getroot())
            SkyTempleMainController.reload_view()

    def on_cr_export_selected_toggled(self, w: Gtk.CellRendererToggle, path, *args):
        store = builder_get_assert(self.builder, Gtk.TreeStore, 'export_dialog_store')
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
                        assert child is not None
                        children.append(child)
                    states = [store[child][5] for child in children]
                    should_be_inconsistent = any([store[child][6] for child in children]) or not states.count(
                        states[0]) == len(states)
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
                assert child is not None
                store[child][5] = is_active
                store[child][6] = False
                mark_active_recurse(child)

        mark_active_recurse(store.get_iter(path))

    def _init_language_labels(self):
        langs = self._string_provider.get_languages()
        for lang_id in range(0, 5):
            gui_id = lang_id + 1
            gui_label = builder_get_assert(self.builder, Gtk.Label, f'label_lang{gui_id}')
            gui_label_cat = builder_get_assert(self.builder, Gtk.Label, f'label_lang{gui_id}_cat')
            gui_entry = builder_get_assert(self.builder, Gtk.Entry, f'entry_lang{gui_id}')
            gui_entry_cat = builder_get_assert(self.builder, Gtk.Entry, f'entry_lang{gui_id}_cat')
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
        if not self.module.project.is_patch_applied("ExpandPokeList"):
            builder_get_assert(self.builder, Gtk.Label, f'label_base_id').set_text(f'#{self.entry.md_index_base:03}')
        else:
            builder_get_assert(self.builder, Gtk.Label, f'label_base_id').set_text(f'See Entity ID')
        name = self._string_provider.get_value(StringType.POKEMON_NAMES, self.entry.md_index_base)
        builder_get_assert(self.builder, Gtk.Label, 'label_id_name').set_text(f'${self.entry.md_index:04d}: {name}')

    def _init_stores(self):
        # Genders
        self._comboxbox_for_enum(['cb_gender'], Gender)
        # Types
        self._comboxbox_for_enum_with_strings(['cb_type_primary', 'cb_type_secondary'], PokeType, StringType.TYPE_NAMES)
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
        # Idle Animation Type
        self._comboxbox_for_enum(['cb_idle_anim'], IdleAnimType)

        # Shadow Size
        self._comboxbox_for_enum(['cb_shadow_size'], ShadowSize)

    def _init_values(self):
        # Names
        langs = self._string_provider.get_languages()
        for lang_id in range(0, 5):
            gui_id = lang_id + 1
            gui_entry = builder_get_assert(self.builder, Gtk.Entry, f'entry_lang{gui_id}')
            gui_entry_cat = builder_get_assert(self.builder, Gtk.Entry, f'entry_lang{gui_id}_cat')
            if lang_id < len(langs):
                # We have this language
                if not self.module.project.is_patch_applied('ExpandPokeList'):
                    idx = self.entry.md_index_base
                else:
                    idx = self.entry.md_index
                gui_entry.set_text(self._string_provider.get_value(StringType.POKEMON_NAMES,
                                                                   idx,
                                                                   langs[lang_id]))
                gui_entry_cat.set_text(self._string_provider.get_value(StringType.POKEMON_CATEGORIES,
                                                                       idx,
                                                                       langs[lang_id]))

        # Stats
        a = self.module.get_idle_anim_type(self.item_id)
        if a is None:
            builder_get_assert(self.builder, Gtk.Widget, 'cb_idle_anim').set_sensitive(False)
        else:
            self._set_cb('cb_idle_anim', a.value)
        self._set_entry('entry_personality', self.module.get_personality(self.item_id))
        self._set_entry('entry_unk31', self.entry.unk31)
        self._set_entry('entry_national_pokedex_number', self.entry.national_pokedex_number)
        self._set_entry('entry_entid', self.entry.entid)
        self._set_entry('entry_sprite_index', self.entry.sprite_index)
        self._set_entry('entry_base_movement_speed', self.entry.base_movement_speed)
        self._set_entry('entry_pre_evo_index', self.entry.pre_evo_index)
        self._set_entry('entry_base_form_index', self.entry.base_form_index)
        self._set_cb('cb_evo_method', self.entry.evo_method)
        self._set_entry('entry_evo_param1', self.entry.evo_param1)
        self._set_cb('cb_evo_param2', self.entry.evo_param2)
        self._set_cb('cb_gender', self.entry.gender)
        self._set_entry('entry_body_size', self.entry.body_size)
        self._set_cb('cb_type_primary', self.entry.type_primary)
        self._set_cb('cb_type_secondary', self.entry.type_secondary)
        self._set_cb('cb_movement_type', self.entry.movement_type)
        self._set_cb('cb_iq_group', self.entry.iq_group)
        self._set_cb('cb_ability_primary', self.entry.ability_primary)
        self._set_cb('cb_ability_secondary', self.entry.ability_secondary)
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
        self._set_cb('cb_shadow_size', self.entry.shadow_size)
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

    def _comboxbox_for_enum(self, names: List[str], enum: Type[Enum], sort_by_name=False):
        store = Gtk.ListStore(int, str)  # id, name
        if sort_by_name:
            enum = sorted(enum, key=lambda x: self._enum_entry_to_str(x))  # type: ignore
        for entry in enum:
            store.append([entry.value, self._enum_entry_to_str(entry)])
        for name in names:
            self._fast_set_comboxbox_store(builder_get_assert(self.builder, Gtk.ComboBox, name), store, 1)

    def _comboxbox_for_enum_with_strings(self, names: List[str], enum: Type[Enum], string_type: StringType):
        store = Gtk.ListStore(int, str)  # id, name
        for entry in enum:
            store.append([entry.value, self._string_provider.get_value(string_type, entry.value)])
        for name in names:
            self._fast_set_comboxbox_store(builder_get_assert(self.builder, Gtk.ComboBox, name), store, 1)

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
        builder_get_assert(self.builder, Gtk.Entry, entry_name).set_text(str(text))

    def _set_cb(self, cb_name, value):
        cb = builder_get_assert(self.builder, Gtk.ComboBox, cb_name)
        l_iter: Gtk.TreeIter = assert_not_none(assert_not_none(cb.get_model()).get_iter_first())
        while l_iter:
            row = cb.get_model()[l_iter]
            if row[0] == value:
                cb.set_active_iter(l_iter)
                return
            l_iter = assert_not_none(assert_not_none(cb.get_model()).iter_next(l_iter))

    def _set_switch(self, switch_name, value):
        builder_get_assert(self.builder, Gtk.Switch, switch_name).set_active(value)

    def _update_from_switch(self, w: Gtk.Switch):
        attr_name = Gtk.Buildable.get_name(w)[7:]
        setattr(self.entry, attr_name, w.get_active())

    def _update_from_cb(self, w: Gtk.ComboBox):
        attr_name = Gtk.Buildable.get_name(w)[3:]
        val = w.get_model()[assert_not_none(w.get_active_iter())][0]
        current_val = getattr(self.entry, attr_name)
        if isinstance(current_val, Enum):
            enum_class = current_val.__class__
            val = enum_class(val)
        setattr(self.entry, attr_name, val)

    def _update_lang_from_entry(self, w: Gtk.Entry, lang_index):
        lang = self._string_provider.get_languages()[lang_index]
        if not self.module.project.is_patch_applied('ExpandPokeList'):
            idx = self.entry.md_index_base
        else:
            idx = self.entry.md_index
        self._string_provider.get_model(lang).strings[
            self._string_provider.get_index(StringType.POKEMON_NAMES, idx)
        ] = w.get_text()
        self.module.update_monster_sort_lists(lang)

    def _update_lang_cat_from_entry(self, w: Gtk.Entry, lang_index):
        if not self.module.project.is_patch_applied('ExpandPokeList'):
            idx = self.entry.md_index_base
        else:
            idx = self.entry.md_index
        lang = self._string_provider.get_languages()[lang_index]
        self._string_provider.get_model(lang).strings[
            self._string_provider.get_index(StringType.POKEMON_CATEGORIES, idx)
        ] = w.get_text()

    def _init_sub_pages(self):
        notebook = builder_get_assert(self.builder, Gtk.Notebook, 'main_notebook')
        tab_label: Gtk.Label = Gtk.Label.new(_('Stats and Moves'))
        level_up_view, self._level_up_controller = self.module.get_level_up_view(self.item_id)
        notebook.append_page(level_up_view, tab_label)
        tab_label = Gtk.Label.new(_('Portraits'))
        notebook.append_page(self.module.get_portrait_view(self.item_id), tab_label)
        self._reload_sprite_page()
        if self._level_up_controller is not None:
            self._show_no_stats_warning(not self._level_up_controller.has_stats)
        else:
            self._show_no_stats_warning(False) # sub entries

    def _reload_sprite_page(self):
        notebook = builder_get_assert(self.builder, Gtk.Notebook, 'main_notebook')
        if self._cached_sprite_page:
            notebook.remove_page(self._cached_sprite_page)
        tab_label: Gtk.Label = Gtk.Label.new(_('Sprites'))
        tab_label.show()
        self._cached_sprite_page = notebook.append_page(
            self.module.get_sprite_view(self.entry.sprite_index, self.item_id), tab_label
        )

    def _show_no_stats_warning(self, reveal: bool):
        info_warning_stats = builder_get_assert(self.builder, Gtk.InfoBar, "info_warning_stats")
        info_warning_stats.set_revealed(reveal)

    def _update_param_label(self):
        label = builder_get_assert(self.builder, Gtk.Label, 'label_param')
        entry = builder_get_assert(self.builder, Gtk.Entry, 'entry_evo_param1')
        cb = builder_get_assert(self.builder, Gtk.ComboBox, 'cb_evo_method')
        val = cb.get_model()[assert_not_none(cb.get_active_iter())][0]
        try:
            entry_id = int(entry.get_text())
            if val == 3:
                if entry_id >= MAX_ITEMS:
                    raise ValueError()
                name = self._string_provider.get_value(StringType.ITEM_NAMES, entry_id)
                label.set_text(f'#{entry_id:03d}: {name}')
            elif val == 4:
                if entry_id > FileType.MD.properties().num_entities:
                    raise ValueError()
                mentry = self.module.monster_md[entry_id]
                if not self.module.project.is_patch_applied('ExpandPokeList'):
                    idx = mentry.md_index_base
                    p = '#'
                else:
                    idx = mentry.md_index
                    p = '$'
                name = self._string_provider.get_value(StringType.POKEMON_NAMES, idx)
                label.set_text(f'{p}{idx:04d}: {name}')
            else:
                label.set_text(f'')
        except BaseException:
            label.set_text(_('??? Enter a valid parameter (#)'))

    def _update_base_form_label(self):
        label = builder_get_assert(self.builder, Gtk.Label, 'label_base_form_index')
        entry = builder_get_assert(self.builder, Gtk.Entry, 'entry_base_form_index')
        try:
            entry_id = int(entry.get_text())
            if entry_id > FileType.MD.properties().num_entities:
                raise ValueError()
            mentry = self.module.monster_md[entry_id]
            if not self.module.project.is_patch_applied('ExpandPokeList'):
                idx = mentry.md_index_base
                p = '#'
            else:
                idx = mentry.md_index
                p = '$'
            name = self._string_provider.get_value(StringType.POKEMON_NAMES, idx)
            label.set_text(f'{p}{idx:04d}: {name}')
        except BaseException:
            label.set_text(_('??? Enter a valid Base ID (#)'))

    def _update_pre_evo_label(self):
        label = builder_get_assert(self.builder, Gtk.Label, 'label_pre_evo_index')
        gtk_entry = builder_get_assert(self.builder, Gtk.Entry, 'entry_pre_evo_index')
        try:
            entry_id = int(gtk_entry.get_text())
            entry: MdEntryProtocol = self.module.monster_md[entry_id]
            if not self.module.project.is_patch_applied('ExpandPokeList'):
                idx = entry.md_index_base
            else:
                idx = entry.md_index
            name = self._string_provider.get_value(StringType.POKEMON_NAMES, idx)
            label.set_text(f'${entry.md_index:04d}: {name} ({Gender(entry.gender).name[0]})')  # type: ignore
        except BaseException:
            label.set_text(_('??? Enter a valid Entry ID ($)'))

    def _update_chance_label(self):
        label1 = builder_get_assert(self.builder, Gtk.Label, 'label_chance_no_drop')
        entry1 = builder_get_assert(self.builder, Gtk.Entry, 'entry_unk27')
        label2 = builder_get_assert(self.builder, Gtk.Label, 'label_chance_normal_items')
        entry2 = builder_get_assert(self.builder, Gtk.Entry, 'entry_unk28')
        label3 = builder_get_assert(self.builder, Gtk.Label, 'label_chance_exclusive1')
        entry3 = builder_get_assert(self.builder, Gtk.Entry, 'entry_unk29')
        label4 = builder_get_assert(self.builder, Gtk.Label, 'label_chance_exclusive2')
        entry4 = builder_get_assert(self.builder, Gtk.Entry, 'entry_unk30')
        try:
            entry1_value = int(entry1.get_text())
            if entry1_value == 0:
                entry1_value = 1
                entry2_value = entry3_value = entry4_value = 0
            else:
                entry2_value = int(entry2.get_text())
                entry3_value = int(entry3.get_text())
                entry4_value = int(entry4.get_text())
            sum_values = entry1_value + entry2_value + entry3_value + entry4_value
            label1.set_text(f'{entry1_value / sum_values * 100:2.02f}%')
            label2.set_text(f'{entry2_value / sum_values * 100:2.02f}%')
            label3.set_text(f'{entry3_value / sum_values * 100:2.02f}%')
            label4.set_text(f'{entry4_value / sum_values * 100:2.02f}%')
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
        md_gender1, md_gender2 = self.module.get_entry_both(getattr(self.entry, self.module.effective_base_attr))
        sprite_size_table = self.module.get_pokemon_sprite_data_table()
        try:
            with self._monster_bin as monster_bin:
                changed = check_and_correct_monster_sprite_size(
                    self.entry,
                    md_gender1=md_gender1,
                    md_gender2=md_gender2,
                    monster_bin=monster_bin,
                    sprite_size_table=sprite_size_table,
                    is_expand_poke_list_patch_applied=self.module.project.is_patch_applied("ExpandPokeList")
                )
            if changed:
                self._set_entry('entry_unk17', self.entry.unk17)
                self._set_entry('entry_unk18', self.entry.unk18)
                self.module.set_pokemon_sprite_data_table(sprite_size_table)

                if show_warning:
                    md = SkyTempleMessageDialog(MainController.window(),
                                                Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.WARNING,
                                                Gtk.ButtonsType.OK,
                                                _("The sprite size of this Pokémon was not consistent "
                                                  "for this Pokémon's assigned sprite.\n"
                                                  "SkyTemple automatically corrected it."))
                    md.set_position(Gtk.WindowPosition.CENTER)
                    md.run()
                    md.destroy()

                self.mark_as_modified()
        except BaseException as ex:
            logger.error("Failed to check Pokémon sprite size.", exc_info=ex)

    # Relative to the new evolution system
    def _init_monster_store(self):
        monster_md = self.module.monster_md
        monster_store = builder_get_assert(self.builder, Gtk.ListStore, 'monster_store')
        for idx, entry in enumerate(monster_md.entries):
            if idx == 0:
                continue
            if not self.module.project.is_patch_applied('ExpandPokeList'):
                sidx = entry.md_index_base
            else:
                sidx = entry.md_index
            name = self.module.project.get_string_provider().get_value(StringType.POKEMON_NAMES, sidx)
            self._ent_names[idx] = f'{name} ({Gender(entry.gender).print_name}) (#{idx:04})'  # type: ignore
            monster_store.append([self._ent_names[idx]])

    def on_cr_entity_editing_started(self, renderer, editable, path):
        editable.set_completion(builder_get_assert(self.builder, Gtk.EntryCompletion, 'completion_entities'))

    def on_btn_help_entid_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("If the 'ExpandPokeList' patch is not applied, this is unused. Note however that it is used to build groups when applying the patches.\n"
              "After the patch is applied, this value defines the Base ID and therefore how Pokémon are grouped.\n"
              "Reload the project after making changes to this value, to reflect them in the tree on the left."),
            title=_("Entity ID")
        )
        md.run()
        md.destroy()

    def on_btn_help_evo_egg_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("For missions with an egg as a reward, the egg contains a random Pokémon that is selected among the child Pokémon of the ones in the spawn list of the mission floor.\n"
              "This list indicates this Pokémon's children. If no children exist, the game will default to that pokémon species. "),
            title=_("Children Info")
        )
        md.run()
        md.destroy()

    def on_btn_help_evo_stats_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("These are the bonuses applied to stats when a Pokémon evolved into that species.\n"
              "Negative values are allowed."),
            title=_("Evolution Bonus Info")
        )
        md.run()
        md.destroy()

    def on_evo_species_edited(self, widget, path, text):
        self._edit_species_store('evo_store', path, text)

    def on_egg_species_edited(self, widget, path, text):
        self._edit_species_store('egg_store', path, text)

    def _edit_species_store(self, store_name, path, text):
        store = builder_get_assert(self.builder, Gtk.ListStore, store_name)
        match = PATTERN.match(text)
        if match is None:
            return
        try:
            entid = int(match.group(1))
        except ValueError:
            return
        # entid:
        store[path][0] = entid
        # ent_name:
        store[path][1] = self._ent_names[entid]
        self._rebuild_evo_lists()

    def _init_evo_lists(self):
        current_evo = self._md_evo.evo_entries[self.item_id]
        current_stats = self._md_evo.evo_stats[self.item_id]
        tree = builder_get_assert(self.builder, Gtk.TreeView, 'evo_tree')
        store = cast(Optional[Gtk.ListStore], tree.get_model())
        assert store is not None
        store.clear()
        for entry in current_evo.evos:
            store.append([
                entry, self._ent_names[entry]
            ])
        tree = builder_get_assert(self.builder, Gtk.TreeView, 'egg_tree')
        store = cast(Optional[Gtk.ListStore], tree.get_model())
        assert store is not None
        store.clear()
        for entry in current_evo.eggs:
            store.append([
                entry, self._ent_names[entry]
            ])
        self._set_entry('entry_hp_bonus', current_stats.hp_bonus)
        self._set_entry('entry_atk_bonus', current_stats.atk_bonus)
        self._set_entry('entry_spatk_bonus', current_stats.spatk_bonus)
        self._set_entry('entry_def_bonus', current_stats.def_bonus)
        self._set_entry('entry_spdef_bonus', current_stats.spdef_bonus)

    @catch_overflow(i16)
    def on_entry_entry_hp_bonus_changed(self, w: Gtk.Entry, *args):
        try:
            val = i16_checked(int(w.get_text()))
        except ValueError:
            return
        self._md_evo.evo_stats[self.item_id].hp_bonus = val
        self.module.mark_md_evo_as_modified(self.item_id)

    @catch_overflow(i16)
    def on_entry_entry_atk_bonus_changed(self, w: Gtk.Entry, *args):
        try:
            val = i16_checked(int(w.get_text()))
        except ValueError:
            return
        self._md_evo.evo_stats[self.item_id].atk_bonus = val
        self.module.mark_md_evo_as_modified(self.item_id)

    @catch_overflow(i16)
    def on_entry_entry_spatk_bonus_changed(self, w: Gtk.Entry, *args):
        try:
            val = i16_checked(int(w.get_text()))
        except ValueError:
            return
        self._md_evo.evo_stats[self.item_id].spatk_bonus = val
        self.module.mark_md_evo_as_modified(self.item_id)

    @catch_overflow(i16)
    def on_entry_entry_def_bonus_changed(self, w: Gtk.Entry, *args):
        try:
            val = i16_checked(int(w.get_text()))
        except ValueError:
            return
        self._md_evo.evo_stats[self.item_id].def_bonus = val
        self.module.mark_md_evo_as_modified(self.item_id)

    @catch_overflow(i16)
    def on_entry_entry_spdef_bonus_changed(self, w: Gtk.Entry, *args):
        try:
            val = i16_checked(int(w.get_text()))
        except ValueError:
            return
        self._md_evo.evo_stats[self.item_id].spdef_bonus = val
        self.module.mark_md_evo_as_modified(self.item_id)

    def on_btn_add_evo_clicked(self, *args):
        try:
            if len(self._md_evo.evo_entries[self.item_id].evos) >= MAX_EVOS:
                raise ValueError(_(f"A pokémon can't evolve into more than {MAX_EVOS} evolutions."))
            else:
                self._add_monster_to_store('evo_tree')
        except ValueError as err:
            display_error(
                sys.exc_info(),
                str(err),
                _("Too much evolutions.")
            )

    def on_btn_add_egg_clicked(self, *args):
        try:
            if len(self._md_evo.evo_entries[self.item_id].eggs) >= MAX_EGGS:
                raise ValueError(_(f"A pokémon can't have more than {MAX_EGGS} children."))
            else:
                self._add_monster_to_store('egg_tree')
        except ValueError as err:
            display_error(
                sys.exc_info(),
                str(err),
                _("Too much children.")
            )

    def _add_monster_to_store(self, tree_name):
        tree = builder_get_assert(self.builder, Gtk.TreeView, tree_name)
        store = cast(Optional[Gtk.ListStore], tree.get_model())
        assert store is not None
        store.append([
            1, self._ent_names[1]
        ])
        self._rebuild_evo_lists()

    def on_btn_remove_evo_clicked(self, *args):
        self._remove_monster_to_store('evo_tree')

    def on_btn_remove_egg_clicked(self, *args):
        self._remove_monster_to_store('egg_tree')

    def _remove_monster_to_store(self, tree_name):
        tree = builder_get_assert(self.builder, Gtk.TreeView, tree_name)
        store = cast(Optional[Gtk.ListStore], tree.get_model())
        assert store is not None
        # Deletes all selected dialogue entries
        # Allows multiple deletion
        active_rows: List[Gtk.TreePath] = tree.get_selection().get_selected_rows()[1]
        for x in reversed(sorted(active_rows, key=lambda x: x.get_indices())):
            del store[x.get_indices()[0]]
        self._rebuild_evo_lists()
        self._init_evo_lists()

    def _rebuild_evo_lists(self):
        tree: Gtk.TreeView = builder_get_assert(self.builder, Gtk.TreeView, 'evo_tree')
        store = cast(Optional[Gtk.ListStore], tree.get_model())
        assert store is not None
        evo_entries = []
        for entry in iter_tree_model(store):
            evo_entries.append(entry[0])
        self._md_evo.evo_entries[self.item_id].evos = evo_entries
        tree = builder_get_assert(self.builder, Gtk.TreeView, 'egg_tree')
        store = cast(Optional[Gtk.ListStore], tree.get_model())
        assert store is not None
        eggs_entries = []
        for entry in iter_tree_model(store):
            eggs_entries.append(entry[0])
        self._md_evo.evo_entries[self.item_id].eggs = eggs_entries
        self.module.mark_md_evo_as_modified(self.item_id)
