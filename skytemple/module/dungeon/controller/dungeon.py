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
from typing import TYPE_CHECKING, Optional

from gi.repository import Gtk
from gi.repository.Gtk import ResponseType
from range_typed_integers import i8, i8_checked, i16, i16_checked

from skytemple.controller.main import MainController
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.module_controller import AbstractController
from skytemple.core.string_provider import StringType
from skytemple.core.ui_utils import catch_overflow, builder_get_assert
from skytemple_files.hardcoded.dungeons import DungeonRestrictionDirection
from skytemple_files.common.i18n_util import _, f

if TYPE_CHECKING:
    from skytemple.module.dungeon.module import DungeonModule, DungeonViewInfo


class DungeonController(AbstractController):
    def __init__(self, module: 'DungeonModule', dungeon_info: 'DungeonViewInfo'):
        self.module = module
        self.dungeon_info = dungeon_info
        self.dungeon_name = self.module.project.get_string_provider().get_value(
            StringType.DUNGEON_NAMES_MAIN, self.dungeon_info.dungeon_id
        )

        self.restrictions = None
        if self.dungeon_info.length_can_be_edited:
            self.restrictions = self.module.get_dungeon_restrictions()[dungeon_info.dungeon_id]

        self.builder: Gtk.Builder = None  # type: ignore
        self._is_loading = True

    # noinspection PyUnusedLocal
    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'dungeon.glade')
        assert self.builder

        builder_get_assert(self.builder, Gtk.Label, 'label_dungeon_name').set_text(self.dungeon_name)
        edit_text = ''

        if not self.dungeon_info.length_can_be_edited:
            edit_text = _('\nSince this is a Dojo Dungeon, the floor count can not be changed.')
            builder_get_assert(self.builder, Gtk.Button, 'edit_floor_count').set_sensitive(False)
            builder_get_assert(self.builder, Gtk.Grid, 'dungeon_restrictions_grid').set_sensitive(False)
        else:
            self._init_dungeon_restrictions()

        floor_count = self.module.get_number_floors(self.dungeon_info.dungeon_id)
        builder_get_assert(self.builder, Gtk.Label, 'label_floor_count').set_text(
            f(_('This dungeon has {floor_count} floors.{edit_text}'))
        )

        self._init_names()
        self._is_loading = False
        self.builder.connect_signals(self)

        return builder_get_assert(self.builder, Gtk.Box, 'main_box')

    def _init_names(self):
        sp = self.module.project.get_string_provider()
        langs = sp.get_languages()
        for lang_id in range(0, 5):
            label_lang = builder_get_assert(self.builder, Gtk.Label, f'label_lang{lang_id}')
            entry_main_lang = builder_get_assert(self.builder, Gtk.Entry, f'entry_main_lang{lang_id}')
            entry_selection_lang = builder_get_assert(self.builder, Gtk.Entry, f'entry_selection_lang{lang_id}')
            entry_script_engine_lang = builder_get_assert(self.builder, Gtk.Entry, f'entry_script_engine_lang{lang_id}')
            entry_banner_lang = builder_get_assert(self.builder, Gtk.Entry, f'entry_banner_lang{lang_id}')
            if lang_id < len(langs):
                # We have this language
                lang = langs[lang_id]
                label_lang.set_text(lang.name)
                entry_main_lang.set_text(
                    sp.get_value(StringType.DUNGEON_NAMES_MAIN, self.dungeon_info.dungeon_id, langs[lang_id]).replace('\n', '\\n')
                )
                entry_selection_lang.set_text(
                    sp.get_value(StringType.DUNGEON_NAMES_SELECTION, self.dungeon_info.dungeon_id, langs[lang_id]).replace('\n', '\\n')
                )
                entry_script_engine_lang.set_text(
                    sp.get_value(StringType.DUNGEON_NAMES_SET_DUNGEON_BANNER, self.dungeon_info.dungeon_id, langs[lang_id]).replace('\n', '\\n')
                )
                entry_banner_lang.set_text(
                    sp.get_value(StringType.DUNGEON_NAMES_BANNER, self.dungeon_info.dungeon_id, langs[lang_id]).replace('\n', '\\n')
                )
                entry_main_lang.set_sensitive(True)
                entry_selection_lang.set_sensitive(True)
                entry_script_engine_lang.set_sensitive(True)
                entry_banner_lang.set_sensitive(True)

    def _init_dungeon_restrictions(self):
        assert self.restrictions is not None
        builder_get_assert(self.builder, Gtk.ComboBox, 'cb_direction').set_active(int(self.restrictions.direction.value))
        builder_get_assert(self.builder, Gtk.Switch, 'switch_enemies_evolve_when_team_member_koed').set_active(self.restrictions.enemies_evolve_when_team_member_koed)
        builder_get_assert(self.builder, Gtk.Switch, 'switch_enemies_grant_exp').set_active(self.restrictions.enemies_grant_exp)
        builder_get_assert(self.builder, Gtk.Switch, 'switch_recruiting_allowed').set_active(self.restrictions.recruiting_allowed)
        builder_get_assert(self.builder, Gtk.Switch, 'switch_level_reset').set_active(self.restrictions.level_reset)
        builder_get_assert(self.builder, Gtk.Switch, 'switch_money_allowed').set_active(not self.restrictions.money_allowed)
        builder_get_assert(self.builder, Gtk.Switch, 'switch_leader_can_be_changed').set_active(self.restrictions.leader_can_be_changed)
        builder_get_assert(self.builder, Gtk.Switch, 'switch_dont_save_before_entering').set_active(not self.restrictions.dont_save_before_entering)
        builder_get_assert(self.builder, Gtk.Switch, 'switch_iq_skills_disabled').set_active(not self.restrictions.iq_skills_disabled)
        builder_get_assert(self.builder, Gtk.Switch, 'switch_traps_remain_invisible_on_attack').set_active(not self.restrictions.traps_remain_invisible_on_attack)
        builder_get_assert(self.builder, Gtk.Switch, 'switch_enemies_can_drop_chests').set_active(self.restrictions.enemies_can_drop_chests)
        builder_get_assert(self.builder, Gtk.Entry, 'entry_max_rescue_attempts').set_text(str(self.restrictions.max_rescue_attempts))
        builder_get_assert(self.builder, Gtk.Entry, 'entry_max_items_allowed').set_text(str(self.restrictions.max_items_allowed))
        builder_get_assert(self.builder, Gtk.Entry, 'entry_max_party_members').set_text(str(self.restrictions.max_party_members))
        builder_get_assert(self.builder, Gtk.Entry, 'entry_turn_limit').set_text(str(self.restrictions.turn_limit))
        builder_get_assert(self.builder, Gtk.Entry, 'entry_random_movement_chance').set_text(str(self.restrictions.random_movement_chance))

    def on_edit_floor_count_clicked(self, *args):
        dialog: Gtk.Dialog = builder_get_assert(self.builder, Gtk.Dialog, 'dialog_adjust_floor_count')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        current_floor_count = self.module.get_number_floors(self.dungeon_info.dungeon_id)

        label_floor_count_in_dialog = builder_get_assert(self.builder, Gtk.Label, 'label_floor_count_in_dialog')
        spin_floor_count = builder_get_assert(self.builder, Gtk.SpinButton, 'spin_floor_count')

        label_floor_count_in_dialog.set_text(f(_('This dungeon currently has {current_floor_count} floors.')))
        spin_floor_count.set_value(current_floor_count)

        resp = dialog.run()
        dialog.hide()
        if resp == ResponseType.APPLY:
            self.module.change_floor_count(self.dungeon_info.dungeon_id, int(spin_floor_count.get_value()))


    # <editor-fold desc="HANDLERS NAMES" defaultstate="collapsed">

    def on_entry_main_lang0_changed(self, entry: Gtk.Entry):
        # TODO: Also update the Dungeon name in the item view
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_MAIN, 0)
        self.mark_as_modified()

    def on_entry_main_lang1_changed(self, entry: Gtk.Entry):
        # TODO: Also update the Group name in the item view
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_MAIN, 1)
        self.mark_as_modified()

    def on_entry_main_lang2_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_MAIN, 2)
        self.mark_as_modified()

    def on_entry_main_lang3_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_MAIN, 3)
        self.mark_as_modified()

    def on_entry_main_lang4_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_MAIN, 4)
        self.mark_as_modified()

    def on_entry_selection_lang0_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_SELECTION, 0)
        self.mark_as_modified()

    def on_entry_selection_lang1_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_SELECTION, 1)
        self.mark_as_modified()

    def on_entry_selection_lang2_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_SELECTION, 2)
        self.mark_as_modified()

    def on_entry_selection_lang3_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_SELECTION, 3)
        self.mark_as_modified()

    def on_entry_selection_lang4_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_SELECTION, 4)
        self.mark_as_modified()

    def on_entry_script_engine_lang0_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_SET_DUNGEON_BANNER, 0)
        self.mark_as_modified()

    def on_entry_script_engine_lang1_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_SET_DUNGEON_BANNER, 1)
        self.mark_as_modified()

    def on_entry_script_engine_lang2_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_SET_DUNGEON_BANNER, 2)
        self.mark_as_modified()

    def on_entry_script_engine_lang3_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_SET_DUNGEON_BANNER, 3)
        self.mark_as_modified()

    def on_entry_script_engine_lang4_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_SET_DUNGEON_BANNER, 4)
        self.mark_as_modified()

    def on_entry_banner_lang0_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_BANNER, 0)
        self.mark_as_modified()

    def on_entry_banner_lang1_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_BANNER, 1)
        self.mark_as_modified()

    def on_entry_banner_lang2_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_BANNER, 2)
        self.mark_as_modified()

    def on_entry_banner_lang3_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_BANNER, 3)
        self.mark_as_modified()

    def on_entry_banner_lang4_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_BANNER, 4)
        self.mark_as_modified()

    # </editor-fold>

    # <editor-fold desc="HANDLERS RESTRICTIONS" defaultstate="collapsed">

    def on_cb_direction_changed(self, w: Gtk.ComboBox, *args):
        assert self.restrictions is not None
        active_id = w.get_active_id()
        if active_id is not None:
            self.restrictions.direction = DungeonRestrictionDirection(int(active_id))
            self._save_dungeon_restrictions()

    def on_switch_enemies_evolve_when_team_member_koed_state_set(self, w: Gtk.Switch, state: bool, *args):
        assert self.restrictions is not None
        self.restrictions.enemies_evolve_when_team_member_koed = state
        self._save_dungeon_restrictions()

    def on_switch_enemies_grant_exp_state_set(self, w: Gtk.Switch, state: bool, *args):
        assert self.restrictions is not None
        self.restrictions.enemies_grant_exp = state
        self._save_dungeon_restrictions()

    def on_switch_recruiting_allowed_state_set(self, w: Gtk.Switch, state: bool, *args):
        assert self.restrictions is not None
        self.restrictions.recruiting_allowed = state
        self._save_dungeon_restrictions()

    def on_switch_level_reset_state_set(self, w: Gtk.Switch, state: bool, *args):
        assert self.restrictions is not None
        self.restrictions.level_reset = state
        self._save_dungeon_restrictions()

    def on_switch_money_allowed_state_set(self, w: Gtk.Switch, state: bool, *args):
        assert self.restrictions is not None
        self.restrictions.money_allowed = not state
        self._save_dungeon_restrictions()

    def on_switch_leader_can_be_changed_state_set(self, w: Gtk.Switch, state: bool, *args):
        assert self.restrictions is not None
        self.restrictions.leader_can_be_changed = state
        self._save_dungeon_restrictions()

    def on_switch_dont_save_before_entering_state_set(self, w: Gtk.Switch, state: bool, *args):
        assert self.restrictions is not None
        self.restrictions.dont_save_before_entering = not state
        self._save_dungeon_restrictions()

    def on_switch_iq_skills_disabled_state_set(self, w: Gtk.Switch, state: bool, *args):
        assert self.restrictions is not None
        self.restrictions.iq_skills_disabled = not state
        self._save_dungeon_restrictions()

    def on_switch_traps_remain_invisible_on_attack_state_set(self, w: Gtk.Switch, state: bool, *args):
        assert self.restrictions is not None
        self.restrictions.traps_remain_invisible_on_attack = not state
        self._save_dungeon_restrictions()

    def on_switch_enemies_can_drop_chests_state_set(self, w: Gtk.Switch, state: bool, *args):
        assert self.restrictions is not None
        self.restrictions.enemies_can_drop_chests = state
        self._save_dungeon_restrictions()

    @catch_overflow(i8)
    def on_entry_max_rescue_attempts_changed(self, w: Gtk.Entry, *args):
        assert self.restrictions is not None
        try:
            value = i8_checked(int(w.get_text()))
        except ValueError:
            return
        self.restrictions.max_rescue_attempts = value
        self._save_dungeon_restrictions()

    @catch_overflow(i8)
    def on_entry_max_items_allowed_changed(self, w: Gtk.Entry, *args):
        assert self.restrictions is not None
        try:
            value = i8_checked(int(w.get_text()))
        except ValueError:
            return
        self.restrictions.max_items_allowed = value
        self._save_dungeon_restrictions()

    @catch_overflow(i8)
    def on_entry_max_party_members_changed(self, w: Gtk.Entry, *args):
        assert self.restrictions is not None
        try:
            value = i8_checked(int(w.get_text()))
        except ValueError:
            return
        self.restrictions.max_party_members = value
        self._save_dungeon_restrictions()

    @catch_overflow(i16)
    def on_entry_turn_limit_changed(self, w: Gtk.Entry, *args):
        assert self.restrictions is not None
        try:
            value = i16_checked(int(w.get_text()))
        except ValueError:
            return
        self.restrictions.turn_limit = value
        self._save_dungeon_restrictions()

    @catch_overflow(i16)
    def on_entry_random_movement_chance_changed(self, w: Gtk.Entry, *args):
        assert self.restrictions is not None
        try:
            value = i16_checked(int(w.get_text()))
        except ValueError:
            return
        self.restrictions.random_movement_chance = value
        self._save_dungeon_restrictions()

    def on_btn_help_random_movement_chance_clicked(self, *args):
        self._help(_("Chance of setting the random movement flag on an enemy when spawning it.\n"
                     "Enemies with this flag set will move randomly inside rooms, instead of heading towards one of "
                     "the exits."))

    def on_btn_help_enemy_evolution_clicked(self, *args):
        self._help(_("If enabled, enemies will evolve after defeating a team member.\n"
                     "The evolution will not happen if the target is revived, if the evolved form of the enemy cannot "
                     "spawn in the current floor or if the sprite of the evolved form is bigger than the sprite of "
                     "the enemy.\n"
                     "Part of this behavior can be modified by applying the BetterEnemyEvolution ASM patch."))

    # </editor-fold>

    def mark_as_modified(self):
        if not self._is_loading:
            self.module.mark_dungeon_as_modified(self.dungeon_info.dungeon_id, False)

    def _save_dungeon_restrictions(self):
        assert self.restrictions is not None
        self.module.update_dungeon_restrictions(self.dungeon_info.dungeon_id, self.restrictions)
        self.mark_as_modified()

    def _update_lang_from_entry(self, w: Gtk.Entry, string_type, lang_index):
        if not self._is_loading:
            sp = self.module.project.get_string_provider()
            lang = sp.get_languages()[lang_index]
            sp.get_model(lang).strings[
                sp.get_index(string_type, self.dungeon_info.dungeon_id)
            ] = w.get_text().replace('\\n', '\n')

    def _help(self, msg):
        md = SkyTempleMessageDialog(MainController.window(),
                                    Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                    Gtk.ButtonsType.OK, msg)
        md.run()
        md.destroy()
