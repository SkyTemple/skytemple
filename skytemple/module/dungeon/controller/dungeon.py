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
from typing import TYPE_CHECKING

from gi.repository import Gtk
from gi.repository.Gtk import ResponseType

from skytemple.controller.main import MainController
from skytemple.core.module_controller import AbstractController
from skytemple.core.string_provider import StringType
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

        self.builder = None
        self._is_loading = True

    # noinspection PyUnusedLocal
    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'dungeon.glade')

        self.builder.get_object('label_dungeon_name').set_text(self.dungeon_name)
        edit_text = ''

        if not self.dungeon_info.length_can_be_edited:
            edit_text = _('\nSince this is a Dojo Dungeon, the floor count can not be changed.')
            self.builder.get_object('edit_floor_count').set_sensitive(False)
            self.builder.get_object('dungeon_restrictions_grid').set_sensitive(False)
        else:
            self._init_dungeon_restrictions()

        floor_count = self.module.get_number_floors(self.dungeon_info.dungeon_id)
        self.builder.get_object('label_floor_count').set_text(
            f(_('This dungeon has {floor_count} floors.{edit_text}'))
        )

        self._init_names()
        self._is_loading = False
        self.builder.connect_signals(self)

        return self.builder.get_object('main_box')

    def _init_names(self):
        sp = self.module.project.get_string_provider()
        langs = sp.get_languages()
        for lang_id in range(0, 5):
            label_lang: Gtk.Entry = self.builder.get_object(f'label_lang{lang_id}')
            entry_main_lang: Gtk.Entry = self.builder.get_object(f'entry_main_lang{lang_id}')
            entry_selection_lang: Gtk.Entry = self.builder.get_object(f'entry_selection_lang{lang_id}')
            entry_script_engine_lang: Gtk.Entry = self.builder.get_object(f'entry_script_engine_lang{lang_id}')
            entry_banner_lang: Gtk.Entry = self.builder.get_object(f'entry_banner_lang{lang_id}')
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
        self.builder.get_object('cb_direction').set_active(int(self.restrictions.direction.value))
        self.builder.get_object('switch_enemies_evolve_when_team_member_koed').set_active(self.restrictions.enemies_evolve_when_team_member_koed)
        self.builder.get_object('switch_enemies_grant_exp').set_active(self.restrictions.enemies_grant_exp)
        self.builder.get_object('switch_recruiting_allowed').set_active(self.restrictions.recruiting_allowed)
        self.builder.get_object('switch_level_reset').set_active(self.restrictions.level_reset)
        self.builder.get_object('switch_money_allowed').set_active(not self.restrictions.money_allowed)
        self.builder.get_object('switch_leader_can_be_changed').set_active(self.restrictions.leader_can_be_changed)
        self.builder.get_object('switch_dont_save_before_entering').set_active(not self.restrictions.dont_save_before_entering)
        self.builder.get_object('switch_iq_skills_disabled').set_active(not self.restrictions.iq_skills_disabled)
        self.builder.get_object('switch_traps_remain_invisible_on_attack').set_active(not self.restrictions.traps_remain_invisible_on_attack)
        self.builder.get_object('switch_enemies_can_drop_chests').set_active(self.restrictions.enemies_can_drop_chests)
        self.builder.get_object('entry_max_rescue_attempts').set_text(str(self.restrictions.max_rescue_attempts))
        self.builder.get_object('entry_max_items_allowed').set_text(str(self.restrictions.max_items_allowed))
        self.builder.get_object('entry_max_party_members').set_text(str(self.restrictions.max_party_members))
        self.builder.get_object('entry_turn_limit').set_text(str(self.restrictions.turn_limit))

    def on_edit_floor_count_clicked(self, *args):
        dialog: Gtk.Dialog = self.builder.get_object('dialog_adjust_floor_count')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        current_floor_count = self.module.get_number_floors(self.dungeon_info.dungeon_id)

        label_floor_count_in_dialog: Gtk.Label = self.builder.get_object('label_floor_count_in_dialog')
        spin_floor_count: Gtk.SpinButton = self.builder.get_object('spin_floor_count')

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
        self.restrictions.direction = DungeonRestrictionDirection(int(w.get_active_id()))
        self._save_dungeon_restrictions()

    def on_switch_enemies_evolve_when_team_member_koed_state_set(self, w: Gtk.Switch, state: bool, *args):
        self.restrictions.enemies_evolve_when_team_member_koed = state
        self._save_dungeon_restrictions()

    def on_switch_enemies_grant_exp_state_set(self, w: Gtk.Switch, state: bool, *args):
        self.restrictions.enemies_grant_exp = state
        self._save_dungeon_restrictions()

    def on_switch_recruiting_allowed_state_set(self, w: Gtk.Switch, state: bool, *args):
        self.restrictions.recruiting_allowed = state
        self._save_dungeon_restrictions()

    def on_switch_level_reset_state_set(self, w: Gtk.Switch, state: bool, *args):
        self.restrictions.level_reset = state
        self._save_dungeon_restrictions()

    def on_switch_money_allowed_state_set(self, w: Gtk.Switch, state: bool, *args):
        self.restrictions.money_allowed = not state
        self._save_dungeon_restrictions()

    def on_switch_leader_can_be_changed_state_set(self, w: Gtk.Switch, state: bool, *args):
        self.restrictions.leader_can_be_changed = state
        self._save_dungeon_restrictions()

    def on_switch_dont_save_before_entering_state_set(self, w: Gtk.Switch, state: bool, *args):
        self.restrictions.dont_save_before_entering = not state
        self._save_dungeon_restrictions()

    def on_switch_iq_skills_disabled_state_set(self, w: Gtk.Switch, state: bool, *args):
        self.restrictions.iq_skills_disabled = not state
        self._save_dungeon_restrictions()

    def on_switch_traps_remain_invisible_on_attack_state_set(self, w: Gtk.Switch, state: bool, *args):
        self.restrictions.traps_remain_invisible_on_attack = not state
        self._save_dungeon_restrictions()

    def on_switch_enemies_can_drop_chests_state_set(self, w: Gtk.Switch, state: bool, *args):
        self.restrictions.enemies_can_drop_chests = state
        self._save_dungeon_restrictions()

    def on_entry_max_rescue_attempts_changed(self, w: Gtk.Entry, *args):
        try:
            value = int(w.get_text())
        except ValueError:
            return
        self.restrictions.max_rescue_attempts = value
        self._save_dungeon_restrictions()

    def on_entry_max_items_allowed_changed(self, w: Gtk.Entry, *args):
        try:
            value = int(w.get_text())
        except ValueError:
            return
        self.restrictions.max_items_allowed = value
        self._save_dungeon_restrictions()

    def on_entry_max_party_members_changed(self, w: Gtk.Entry, *args):
        try:
            value = int(w.get_text())
        except ValueError:
            return
        self.restrictions.max_party_members = value
        self._save_dungeon_restrictions()

    def on_entry_turn_limit_changed(self, w: Gtk.Entry, *args):
        try:
            value = int(w.get_text())
        except ValueError:
            return
        self.restrictions.turn_limit = value
        self._save_dungeon_restrictions()

    # </editor-fold>

    def mark_as_modified(self):
        if not self._is_loading:
            self.module.mark_dungeon_as_modified(self.dungeon_info.dungeon_id, False)

    def _save_dungeon_restrictions(self):
        self.module.update_dungeon_restrictions(self.dungeon_info.dungeon_id, self.restrictions)
        self.mark_as_modified()

    def _update_lang_from_entry(self, w: Gtk.Entry, string_type, lang_index):
        if not self._is_loading:
            sp = self.module.project.get_string_provider()
            lang = sp.get_languages()[lang_index]
            sp.get_model(lang).strings[
                sp.get_index(string_type, self.dungeon_info.dungeon_id)
            ] = w.get_text()
