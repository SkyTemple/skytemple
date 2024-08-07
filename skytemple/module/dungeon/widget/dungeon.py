#  Copyright 2020-2024 Capypara and the SkyTemple Contributors
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
from __future__ import annotations

from typing import TYPE_CHECKING, cast

from gi.repository import Gtk
from gi.repository.Gtk import ResponseType
from range_typed_integers import i8, i8_checked, i16, i16_checked
from skytemple_files.common.i18n_util import _, f
from skytemple_files.hardcoded.dungeons import DungeonRestrictionDirection

from skytemple.controller.main import MainController
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.string_provider import StringType
from skytemple.core.ui_utils import catch_overflow, data_dir, safe_destroy
from skytemple.init_locale import LocalePatchedGtkTemplate

if TYPE_CHECKING:
    from skytemple.module.dungeon.module import DungeonModule, DungeonViewInfo
import os


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "dungeon", "dungeon.ui"))
class StDungeonDungeonPage(Gtk.Box):
    __gtype_name__ = "StDungeonDungeonPage"
    module: DungeonModule
    item_data: DungeonViewInfo
    cb_direction_store: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    label_dungeon_name: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    label_lang1: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    label_lang0: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    label_lang3: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    label_lang2: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    label_lang4: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    entry_main_lang0: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_main_lang1: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_main_lang2: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_main_lang3: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_main_lang4: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_selection_lang0: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_selection_lang1: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_selection_lang2: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_selection_lang3: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_selection_lang4: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_script_engine_lang0: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_script_engine_lang1: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_script_engine_lang2: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_script_engine_lang3: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_script_engine_lang4: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_banner_lang0: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_banner_lang1: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_banner_lang2: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_banner_lang3: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_banner_lang4: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    dungeon_restrictions_grid: Gtk.Grid = cast(Gtk.Grid, Gtk.Template.Child())
    cb_direction: Gtk.ComboBox = cast(Gtk.ComboBox, Gtk.Template.Child())
    switch_level_reset: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    switch_iq_skills_disabled: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    entry_max_rescue_attempts: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_random_movement_chance: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    switch_recruiting_allowed: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    switch_dont_save_before_entering: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    entry_turn_limit: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    switch_enemies_grant_exp: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    switch_leader_can_be_changed: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    switch_enemies_can_drop_chests: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    entry_max_party_members: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    switch_enemies_evolve_when_team_member_koed: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    switch_money_allowed: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    switch_traps_remain_invisible_on_attack: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    entry_max_items_allowed: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    btn_help_random_movement_chance: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    btn_help_enemy_evolution: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    edit_floor_count: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    label_floor_count: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    spin_floor_count_adjument: Gtk.Adjustment = cast(Gtk.Adjustment, Gtk.Template.Child())
    dialog_adjust_floor_count: Gtk.Dialog = cast(Gtk.Dialog, Gtk.Template.Child())
    button1: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    button2: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    label_floor_count_in_dialog: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    spin_floor_count: Gtk.SpinButton = cast(Gtk.SpinButton, Gtk.Template.Child())

    def __init__(self, module: DungeonModule, item_data: DungeonViewInfo):
        super().__init__()
        self.module = module
        self.item_data = item_data
        self.dungeon_name = self.module.project.get_string_provider().get_value(
            StringType.DUNGEON_NAMES_MAIN, self.item_data.dungeon_id
        )
        self.restrictions = None
        if self.item_data.length_can_be_edited:
            self.restrictions = self.module.get_dungeon_restrictions()[item_data.dungeon_id]
        self._is_loading = True
        self.label_dungeon_name.set_text(self.dungeon_name)
        edit_text = ""
        if not self.item_data.length_can_be_edited:
            edit_text = _("\nSince this is a Dojo Dungeon, the floor count can not be changed.")
            self.edit_floor_count.set_sensitive(False)
            self.dungeon_restrictions_grid.set_sensitive(False)
        else:
            self._init_dungeon_restrictions()
        floor_count = self.module.get_number_floors(self.item_data.dungeon_id)
        self.label_floor_count.set_text(f(_("This dungeon has {floor_count} floors.{edit_text}")))
        self._init_names()
        self._is_loading = False

    @Gtk.Template.Callback()
    def on_self_destroy(self, *args):
        # Try to destroy all top-level widgets outside of the template to not leak memory.
        safe_destroy(self.dialog_adjust_floor_count)

    def _init_names(self):
        sp = self.module.project.get_string_provider()
        langs = sp.get_languages()
        for lang_id in range(0, 5):
            label_lang = getattr(self, f"label_lang{lang_id}")
            entry_main_lang = getattr(self, f"entry_main_lang{lang_id}")
            entry_selection_lang = getattr(self, f"entry_selection_lang{lang_id}")
            entry_script_engine_lang = getattr(self, f"entry_script_engine_lang{lang_id}")
            entry_banner_lang = getattr(self, f"entry_banner_lang{lang_id}")
            if lang_id < len(langs):
                # We have this language
                lang = langs[lang_id]
                label_lang.set_text(lang.name)
                entry_main_lang.set_text(
                    sp.get_value(
                        StringType.DUNGEON_NAMES_MAIN,
                        self.item_data.dungeon_id,
                        langs[lang_id],
                    ).replace("\n", "\\n")
                )
                entry_selection_lang.set_text(
                    sp.get_value(
                        StringType.DUNGEON_NAMES_SELECTION,
                        self.item_data.dungeon_id,
                        langs[lang_id],
                    ).replace("\n", "\\n")
                )
                entry_script_engine_lang.set_text(
                    sp.get_value(
                        StringType.DUNGEON_NAMES_SET_DUNGEON_BANNER,
                        self.item_data.dungeon_id,
                        langs[lang_id],
                    ).replace("\n", "\\n")
                )
                entry_banner_lang.set_text(
                    sp.get_value(
                        StringType.DUNGEON_NAMES_BANNER,
                        self.item_data.dungeon_id,
                        langs[lang_id],
                    ).replace("\n", "\\n")
                )
                entry_main_lang.set_sensitive(True)
                entry_selection_lang.set_sensitive(True)
                entry_script_engine_lang.set_sensitive(True)
                entry_banner_lang.set_sensitive(True)

    def _init_dungeon_restrictions(self):
        assert self.restrictions is not None
        self.cb_direction.set_active(int(self.restrictions.direction.value))
        self.switch_enemies_evolve_when_team_member_koed.set_active(
            self.restrictions.enemies_evolve_when_team_member_koed
        )
        self.switch_enemies_grant_exp.set_active(self.restrictions.enemies_grant_exp)
        self.switch_recruiting_allowed.set_active(self.restrictions.recruiting_allowed)
        self.switch_level_reset.set_active(self.restrictions.level_reset)
        self.switch_money_allowed.set_active(not self.restrictions.money_allowed)
        self.switch_leader_can_be_changed.set_active(self.restrictions.leader_can_be_changed)
        self.switch_dont_save_before_entering.set_active(not self.restrictions.dont_save_before_entering)
        self.switch_iq_skills_disabled.set_active(not self.restrictions.iq_skills_disabled)
        self.switch_traps_remain_invisible_on_attack.set_active(not self.restrictions.traps_remain_invisible_on_attack)
        self.switch_enemies_can_drop_chests.set_active(self.restrictions.enemies_can_drop_chests)
        self.entry_max_rescue_attempts.set_text(str(self.restrictions.max_rescue_attempts))
        self.entry_max_items_allowed.set_text(str(self.restrictions.max_items_allowed))
        self.entry_max_party_members.set_text(str(self.restrictions.max_party_members))
        self.entry_turn_limit.set_text(str(self.restrictions.turn_limit))
        self.entry_random_movement_chance.set_text(str(self.restrictions.random_movement_chance))

    @Gtk.Template.Callback()
    def on_edit_floor_count_clicked(self, *args):
        dialog: Gtk.Dialog = self.dialog_adjust_floor_count
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())
        current_floor_count = self.module.get_number_floors(self.item_data.dungeon_id)
        label_floor_count_in_dialog = self.label_floor_count_in_dialog
        spin_floor_count = self.spin_floor_count
        label_floor_count_in_dialog.set_text(f(_("This dungeon currently has {current_floor_count} floors.")))
        spin_floor_count.set_value(current_floor_count)
        resp = dialog.run()
        dialog.hide()
        if resp == ResponseType.APPLY:
            self.module.change_floor_count(self.item_data.dungeon_id, int(spin_floor_count.get_value()))

    # <editor-fold desc="HANDLERS NAMES" defaultstate="collapsed">

    @Gtk.Template.Callback()
    def on_entry_main_lang0_changed(self, entry: Gtk.Entry):
        # TODO: Also update the Dungeon name in the item view
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_MAIN, 0)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_entry_main_lang1_changed(self, entry: Gtk.Entry):
        # TODO: Also update the Group name in the item view
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_MAIN, 1)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_entry_main_lang2_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_MAIN, 2)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_entry_main_lang3_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_MAIN, 3)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_entry_main_lang4_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_MAIN, 4)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_entry_selection_lang0_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_SELECTION, 0)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_entry_selection_lang1_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_SELECTION, 1)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_entry_selection_lang2_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_SELECTION, 2)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_entry_selection_lang3_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_SELECTION, 3)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_entry_selection_lang4_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_SELECTION, 4)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_entry_script_engine_lang0_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_SET_DUNGEON_BANNER, 0)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_entry_script_engine_lang1_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_SET_DUNGEON_BANNER, 1)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_entry_script_engine_lang2_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_SET_DUNGEON_BANNER, 2)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_entry_script_engine_lang3_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_SET_DUNGEON_BANNER, 3)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_entry_script_engine_lang4_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_SET_DUNGEON_BANNER, 4)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_entry_banner_lang0_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_BANNER, 0)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_entry_banner_lang1_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_BANNER, 1)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_entry_banner_lang2_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_BANNER, 2)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_entry_banner_lang3_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_BANNER, 3)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_entry_banner_lang4_changed(self, entry: Gtk.Entry):
        self._update_lang_from_entry(entry, StringType.DUNGEON_NAMES_BANNER, 4)
        self.mark_as_modified()

    # </editor-fold>
    # <editor-fold desc="HANDLERS RESTRICTIONS" defaultstate="collapsed">

    @Gtk.Template.Callback()
    def on_cb_direction_changed(self, w: Gtk.ComboBox, *args):
        assert self.restrictions is not None
        active_id = w.get_active_id()
        if active_id is not None:
            self.restrictions.direction = DungeonRestrictionDirection(int(active_id))
            self._save_dungeon_restrictions()

    @Gtk.Template.Callback()
    def on_switch_enemies_evolve_when_team_member_koed_state_set(self, w: Gtk.Switch, state: bool, *args):
        assert self.restrictions is not None
        self.restrictions.enemies_evolve_when_team_member_koed = state
        self._save_dungeon_restrictions()

    @Gtk.Template.Callback()
    def on_switch_enemies_grant_exp_state_set(self, w: Gtk.Switch, state: bool, *args):
        assert self.restrictions is not None
        self.restrictions.enemies_grant_exp = state
        self._save_dungeon_restrictions()

    @Gtk.Template.Callback()
    def on_switch_recruiting_allowed_state_set(self, w: Gtk.Switch, state: bool, *args):
        assert self.restrictions is not None
        self.restrictions.recruiting_allowed = state
        self._save_dungeon_restrictions()

    @Gtk.Template.Callback()
    def on_switch_level_reset_state_set(self, w: Gtk.Switch, state: bool, *args):
        assert self.restrictions is not None
        self.restrictions.level_reset = state
        self._save_dungeon_restrictions()

    @Gtk.Template.Callback()
    def on_switch_money_allowed_state_set(self, w: Gtk.Switch, state: bool, *args):
        assert self.restrictions is not None
        self.restrictions.money_allowed = not state
        self._save_dungeon_restrictions()

    @Gtk.Template.Callback()
    def on_switch_leader_can_be_changed_state_set(self, w: Gtk.Switch, state: bool, *args):
        assert self.restrictions is not None
        self.restrictions.leader_can_be_changed = state
        self._save_dungeon_restrictions()

    @Gtk.Template.Callback()
    def on_switch_dont_save_before_entering_state_set(self, w: Gtk.Switch, state: bool, *args):
        assert self.restrictions is not None
        self.restrictions.dont_save_before_entering = not state
        self._save_dungeon_restrictions()

    @Gtk.Template.Callback()
    def on_switch_iq_skills_disabled_state_set(self, w: Gtk.Switch, state: bool, *args):
        assert self.restrictions is not None
        self.restrictions.iq_skills_disabled = not state
        self._save_dungeon_restrictions()

    @Gtk.Template.Callback()
    def on_switch_traps_remain_invisible_on_attack_state_set(self, w: Gtk.Switch, state: bool, *args):
        assert self.restrictions is not None
        self.restrictions.traps_remain_invisible_on_attack = not state
        self._save_dungeon_restrictions()

    @Gtk.Template.Callback()
    def on_switch_enemies_can_drop_chests_state_set(self, w: Gtk.Switch, state: bool, *args):
        assert self.restrictions is not None
        self.restrictions.enemies_can_drop_chests = state
        self._save_dungeon_restrictions()

    @Gtk.Template.Callback()
    @catch_overflow(i8)
    def on_entry_max_rescue_attempts_changed(self, w: Gtk.Entry, *args):
        assert self.restrictions is not None
        try:
            value = i8_checked(int(w.get_text()))
        except ValueError:
            return
        self.restrictions.max_rescue_attempts = value
        self._save_dungeon_restrictions()

    @Gtk.Template.Callback()
    @catch_overflow(i8)
    def on_entry_max_items_allowed_changed(self, w: Gtk.Entry, *args):
        assert self.restrictions is not None
        try:
            value = i8_checked(int(w.get_text()))
        except ValueError:
            return
        self.restrictions.max_items_allowed = value
        self._save_dungeon_restrictions()

    @Gtk.Template.Callback()
    @catch_overflow(i8)
    def on_entry_max_party_members_changed(self, w: Gtk.Entry, *args):
        assert self.restrictions is not None
        try:
            value = i8_checked(int(w.get_text()))
        except ValueError:
            return
        self.restrictions.max_party_members = value
        self._save_dungeon_restrictions()

    @Gtk.Template.Callback()
    @catch_overflow(i16)
    def on_entry_turn_limit_changed(self, w: Gtk.Entry, *args):
        assert self.restrictions is not None
        try:
            value = i16_checked(int(w.get_text()))
        except ValueError:
            return
        self.restrictions.turn_limit = value
        self._save_dungeon_restrictions()

    @Gtk.Template.Callback()
    @catch_overflow(i16)
    def on_entry_random_movement_chance_changed(self, w: Gtk.Entry, *args):
        assert self.restrictions is not None
        try:
            value = i16_checked(int(w.get_text()))
        except ValueError:
            return
        self.restrictions.random_movement_chance = value
        self._save_dungeon_restrictions()

    @Gtk.Template.Callback()
    def on_btn_help_random_movement_chance_clicked(self, *args):
        self._help(
            _(
                "Chance of setting the random movement flag on an enemy when spawning it.\nEnemies with this flag set will move randomly inside rooms, instead of heading towards one of the exits."
            )
        )

    @Gtk.Template.Callback()
    def on_btn_help_enemy_evolution_clicked(self, *args):
        self._help(
            _(
                "If enabled, enemies will evolve after defeating a team member.\nThe evolution will not happen if the target is revived, if the evolved form of the enemy cannot spawn in the current floor or if the sprite of the evolved form is bigger than the sprite of the enemy.\nPart of this behavior can be modified by applying the BetterEnemyEvolution ASM patch."
            )
        )

    # </editor-fold>

    def mark_as_modified(self):
        if not self._is_loading:
            self.module.mark_dungeon_as_modified(self.item_data.dungeon_id, False)

    def _save_dungeon_restrictions(self):
        assert self.restrictions is not None
        self.module.update_dungeon_restrictions(self.item_data.dungeon_id, self.restrictions)
        self.mark_as_modified()

    def _update_lang_from_entry(self, w: Gtk.Entry, string_type, lang_index):
        if not self._is_loading:
            sp = self.module.project.get_string_provider()
            lang = sp.get_languages()[lang_index]
            sp.get_model(lang).strings[sp.get_index(string_type, self.item_data.dungeon_id)] = w.get_text().replace(
                "\\n", "\n"
            )

    def _help(self, msg):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            msg,
        )
        md.run()
        md.destroy()
