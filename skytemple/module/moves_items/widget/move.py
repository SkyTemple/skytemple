#  Copyright 2020-2025 SkyTemple Contributors
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
import logging
import typing
from enum import Enum
from typing import TYPE_CHECKING, Optional, cast
from gi.repository import Gtk
from range_typed_integers import u16, u16_checked, u8, u8_checked
from skytemple.controller.main import MainController
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.string_provider import StringType
from skytemple.core.ui_utils import catch_overflow, assert_not_none, data_dir
from skytemple_files.common.i18n_util import _
from skytemple_files.data.md.protocol import PokeType
from skytemple_files.data.waza_p.protocol import (
    WazaMoveCategory,
    WazaMoveRangeTarget,
    WazaMoveRangeRange,
    WazaMoveRangeCondition,
    WazaMoveProtocol,
)

from skytemple.init_locale import LocalePatchedGtkTemplate

if TYPE_CHECKING:
    from skytemple.module.moves_items.module import MovesItemsModule
logger = logging.getLogger(__name__)
import os


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "moves_items", "move.ui"))
class StMovesItemsMovePage(Gtk.Box):
    __gtype_name__ = "StMovesItemsMovePage"
    module: MovesItemsModule
    item_data: int
    buff_lang1_desc: Gtk.TextBuffer = cast(Gtk.TextBuffer, Gtk.Template.Child())
    buff_lang2_desc: Gtk.TextBuffer = cast(Gtk.TextBuffer, Gtk.Template.Child())
    buff_lang3_desc: Gtk.TextBuffer = cast(Gtk.TextBuffer, Gtk.Template.Child())
    buff_lang4_desc: Gtk.TextBuffer = cast(Gtk.TextBuffer, Gtk.Template.Child())
    buff_lang5_desc: Gtk.TextBuffer = cast(Gtk.TextBuffer, Gtk.Template.Child())
    label_id_name: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    cb_type: Gtk.ComboBox = cast(Gtk.ComboBox, Gtk.Template.Child())
    entry_move_id: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_base_power: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_base_pp: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    cb_category: Gtk.ComboBox = cast(Gtk.ComboBox, Gtk.Template.Child())
    label_lang1: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    label_lang2: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    label_lang3: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    label_lang4: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    label_lang5: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    entry_lang1: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_lang2: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_lang3: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_lang4: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_lang5: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    label_lang1_desc: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    label_lang2_desc: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    label_lang3_desc: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    label_lang4_desc: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    label_lang5_desc: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    view_lang1_desc: Gtk.TextView = cast(Gtk.TextView, Gtk.Template.Child())
    view_lang2_desc: Gtk.TextView = cast(Gtk.TextView, Gtk.Template.Child())
    view_lang3_desc: Gtk.TextView = cast(Gtk.TextView, Gtk.Template.Child())
    view_lang4_desc: Gtk.TextView = cast(Gtk.TextView, Gtk.Template.Child())
    view_lang5_desc: Gtk.TextView = cast(Gtk.TextView, Gtk.Template.Child())
    entry_accuracy: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_miss_accuracy: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    btn_help_miss_accuracy: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    entry_number_chained_hits: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    btn_help_number_chained_hits: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    entry_max_upgrade_level: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_crit_chance: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    btn_help_accuracy: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    btn_help_settings_range: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    cb_settings_range_target: Gtk.ComboBox = cast(Gtk.ComboBox, Gtk.Template.Child())
    cb_settings_range_range: Gtk.ComboBox = cast(Gtk.ComboBox, Gtk.Template.Child())
    btn_help_settings_range_ai: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    cb_settings_range_ai_target: Gtk.ComboBox = cast(Gtk.ComboBox, Gtk.Template.Child())
    cb_settings_range_ai_range: Gtk.ComboBox = cast(Gtk.ComboBox, Gtk.Template.Child())
    cb_settings_range_ai_condition: Gtk.ComboBox = cast(Gtk.ComboBox, Gtk.Template.Child())
    entry_ai_weight: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    btn_help_settings_range_ai_condition: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    entry_ai_condition1_chance: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_range_check_text: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    switch_affected_by_magic_coat: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    switch_is_snatchable: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    switch_uses_mouth: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    switch_ignores_taunted: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    btn_help_affected_by_magic_coat: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    btn_help_is_snatchable: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    btn_help_uses_mouth: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    btn_help_ignores_taunted: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    btn_help_message_id: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    entry_message_id: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    btn_help_range_check_text: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    btn_help_ai_frozen_check: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    switch_ai_frozen_check: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    export_dialog_store: Gtk.TreeStore = cast(Gtk.TreeStore, Gtk.Template.Child())
    store_completion_items: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    completion_items: Gtk.EntryCompletion = cast(Gtk.EntryCompletion, Gtk.Template.Child())
    completion_items1: Gtk.EntryCompletion = cast(Gtk.EntryCompletion, Gtk.Template.Child())
    completion_items2: Gtk.EntryCompletion = cast(Gtk.EntryCompletion, Gtk.Template.Child())
    completion_items3: Gtk.EntryCompletion = cast(Gtk.EntryCompletion, Gtk.Template.Child())

    def __init__(self, module: MovesItemsModule, item_data: int):
        super().__init__()
        self.module = module
        self.item_data = item_data
        self.move: WazaMoveProtocol = self.module.get_move(item_data)
        self._string_provider = module.project.get_string_provider()
        self._is_loading = True
        self._init_language_labels()
        self._init_entid()
        self._init_stores()
        self._is_loading = True
        self._init_values()
        self._is_loading = False

    @typing.no_type_check
    def unload(self):
        super().unload()
        self.module = None
        self.move_id = None
        self.move = None
        self._string_provider = None
        self._is_loading = True

    @Gtk.Template.Callback()
    @catch_overflow(u16)
    def on_entry_move_id_changed(self, w, *args):
        try:
            val = u16_checked(int(w.get_text()))
        except ValueError:
            return
        self.move.move_id = val
        self.mark_as_modified()

    @Gtk.Template.Callback()
    @catch_overflow(u16)
    def on_entry_base_power_changed(self, w, *args):
        try:
            val = u16_checked(int(w.get_text()))
        except ValueError:
            return
        self.move.base_power = val
        self.mark_as_modified()

    @Gtk.Template.Callback()
    @catch_overflow(u8)
    def on_entry_base_pp_changed(self, w, *args):
        try:
            val = u8_checked(int(w.get_text()))
        except ValueError:
            return
        self.move.base_pp = val
        self.mark_as_modified()

    @Gtk.Template.Callback()
    @catch_overflow(u8)
    def on_entry_accuracy_changed(self, w, *args):
        try:
            val = u8_checked(int(w.get_text()))
        except ValueError:
            return
        self.move.accuracy = val
        self.mark_as_modified()

    @Gtk.Template.Callback()
    @catch_overflow(u8)
    def on_entry_miss_accuracy_changed(self, w, *args):
        try:
            val = u8_checked(int(w.get_text()))
        except ValueError:
            return
        self.move.miss_accuracy = val
        self.mark_as_modified()

    @Gtk.Template.Callback()
    @catch_overflow(u8)
    def on_entry_max_upgrade_level_changed(self, w, *args):
        try:
            val = u8_checked(int(w.get_text()))
        except ValueError:
            return
        self.move.max_upgrade_level = val
        self.mark_as_modified()

    @Gtk.Template.Callback()
    @catch_overflow(u8)
    def on_entry_crit_chance_changed(self, w, *args):
        try:
            val = u8_checked(int(w.get_text()))
        except ValueError:
            return
        self.move.crit_chance = val
        self.mark_as_modified()

    @Gtk.Template.Callback()
    @catch_overflow(u8)
    def on_entry_number_chained_hits_changed(self, w, *args):
        try:
            val = u8_checked(int(w.get_text()))
        except ValueError:
            return
        self.move.number_chained_hits = val
        self.mark_as_modified()

    @Gtk.Template.Callback()
    @catch_overflow(u8)
    def on_entry_ai_weight_changed(self, w, *args):
        try:
            val = u8_checked(int(w.get_text()))
        except ValueError:
            return
        self.move.ai_weight = val
        self.mark_as_modified()

    @Gtk.Template.Callback()
    @catch_overflow(u8)
    def on_entry_ai_condition1_chance_changed(self, w, *args):
        try:
            val = u8_checked(int(w.get_text()))
        except ValueError:
            return
        self.move.ai_condition1_chance = val
        self.mark_as_modified()

    @Gtk.Template.Callback()
    @catch_overflow(u8)
    def on_entry_range_check_text_changed(self, w, *args):
        try:
            val = u8_checked(int(w.get_text()))
        except ValueError:
            return
        self.move.range_check_text = val
        self.mark_as_modified()

    @Gtk.Template.Callback()
    @catch_overflow(u8)
    def on_entry_message_id_changed(self, w, *args):
        try:
            val = u8_checked(int(w.get_text()))
        except ValueError:
            return
        self.move.message_id = val
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_cb_type_changed(self, w, *args):
        self._update_from_cb(w)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_cb_category_changed(self, w, *args):
        self._update_from_cb(w)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_cb_settings_range_range_changed(self, w, *args):
        val = w.get_model()[w.get_active_iter()][0]
        self.move.settings_range.range = WazaMoveRangeRange(val).value  # type: ignore
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_cb_settings_range_target_changed(self, w, *args):
        val = w.get_model()[w.get_active_iter()][0]
        self.move.settings_range.target = WazaMoveRangeTarget(val).value  # type: ignore
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_cb_settings_range_ai_target_changed(self, w, *args):
        val = w.get_model()[w.get_active_iter()][0]
        self.move.settings_range_ai.target = WazaMoveRangeTarget(val).value  # type: ignore
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_cb_settings_range_ai_range_changed(self, w, *args):
        val = w.get_model()[w.get_active_iter()][0]
        self.move.settings_range_ai.range = WazaMoveRangeRange(val).value  # type: ignore
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_cb_settings_range_ai_condition_changed(self, w, *args):
        val = w.get_model()[w.get_active_iter()][0]
        self.move.settings_range_ai.condition = WazaMoveRangeCondition(val).value  # type: ignore
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_switch_affected_by_magic_coat_state_set(self, w, *args):
        self._update_from_switch(w)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_switch_is_snatchable_state_set(self, w, *args):
        self._update_from_switch(w)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_switch_uses_mouth_state_set(self, w, *args):
        self._update_from_switch(w)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_switch_ignores_taunted_state_set(self, w, *args):
        self._update_from_switch(w)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_switch_ai_frozen_check_state_set(self, w, *args):
        self._update_from_switch(w)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_entry_lang1_changed(self, w, *args):
        # TODO: Update name in tree
        self._update_lang_from_entry(w, 0)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_entry_lang2_changed(self, w, *args):
        self._update_lang_from_entry(w, 1)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_entry_lang3_changed(self, w, *args):
        self._update_lang_from_entry(w, 2)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_entry_lang4_changed(self, w, *args):
        self._update_lang_from_entry(w, 3)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_entry_lang5_changed(self, w, *args):
        self._update_lang_from_entry(w, 4)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_buff_lang1_desc_changed(self, w, *args):
        self._update_lang_desc_from_buffer(w, 0)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_buff_lang2_desc_changed(self, w, *args):
        self._update_lang_desc_from_buffer(w, 1)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_buff_lang3_desc_changed(self, w, *args):
        self._update_lang_desc_from_buffer(w, 2)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_buff_lang4_desc_changed(self, w, *args):
        self._update_lang_desc_from_buffer(w, 3)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_buff_lang5_desc_changed(self, w, *args):
        self._update_lang_desc_from_buffer(w, 4)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_btn_help_accuracy_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _(
                "The percentage indicating the chances the move will succeed. 100 is perfect accuracy. Anything higher than 100 is a never-miss move."
            ),
            title=_("Accuracy:")[:-1],
        )
        md.run()
        md.destroy()

    @Gtk.Template.Callback()
    def on_btn_help_miss_accuracy_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _(
                "Seems to be a second sort of accuracy check. A different message will be shown if this accuracy test fails."
            ),
            title=_("Miss Accuracy:")[:-1],
        )
        md.run()
        md.destroy()

    @Gtk.Template.Callback()
    def on_btn_help_number_chained_hits_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("Possibly the number of times a move hits in a row."),
            title=_("# of chained hits:")[:-1],
        )
        md.run()
        md.destroy()

    @Gtk.Template.Callback()
    def on_btn_help_settings_range_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("These are the range settings that the game uses for processing the actual move."),
            title=_("Actual values:")[:-1],
        )
        md.run()
        md.destroy()

    @Gtk.Template.Callback()
    def on_btn_help_settings_range_ai_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _(
                "When deciding what move to use, the AI will treat the move like it actually has the range settings configured here."
            )
            + _(
                '\nDue to a bug, if the values are "straight line", "In front; cuts corners" or "Two tiles away; cuts corners" are chosen here, the AI range is used as the ACTUAL range of the move.'
            ),
            title=_("Values used for AI calculation:")[:-1],
        )
        md.run()
        md.destroy()

    @Gtk.Template.Callback()
    def on_btn_help_settings_range_ai_condition_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("The Pokémon must be in this condition in order for this move to be used."),
            title=_("Required condition:")[:-1],
        )
        md.run()
        md.destroy()

    @Gtk.Template.Callback()
    def on_btn_help_affected_by_magic_coat_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("Whether the move is affected by magic coat."),
            title=_("Affected by Magic Coat:")[:-1],
        )
        md.run()
        md.destroy()

    @Gtk.Template.Callback()
    def on_btn_help_is_snatchable_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("Whether the move is affected by snatch."),
            title=_("Is Snatchable:")[:-1],
        )
        md.run()
        md.destroy()

    @Gtk.Template.Callback()
    def on_btn_help_uses_mouth_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _('Whether the move is disabled by the "muzzled" status.'),
            title=_("Uses Mouth:")[:-1],
        )
        md.run()
        md.destroy()

    @Gtk.Template.Callback()
    def on_btn_help_ignores_taunted_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("Whether the move can be used while taunted."),
            title=_("Ignores Taunted:")[:-1],
        )
        md.run()
        md.destroy()

    @Gtk.Template.Callback()
    def on_btn_help_message_id_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _(
                "Message ID offset that is displayed for the move. 0 uses the Text String 3860. Higher values select the strings after that (offsets)."
            ),
            title=_("Message ID:")[:-1],
        )
        md.run()
        md.destroy()

    @Gtk.Template.Callback()
    def on_btn_help_ai_frozen_check_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("Whether the AI with Status Checker can select this move when the target is frozen."),
            title=_("AI - Don't use on Frozen:")[:-1],
        )
        md.run()
        md.destroy()

    @Gtk.Template.Callback()
    def on_btn_help_range_check_text_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _(
                "Text string to display to describe the range of the move. 0 uses the Text String 10095/10097 (US/EU). Higher values select the strings after that (offsets)."
            ),
            title=_("Text String ID for Range Text:")[:-1],
        )
        md.run()
        md.destroy()

    def _init_language_labels(self):
        langs = self._string_provider.get_languages()
        for lang_id in range(0, 5):
            gui_id = lang_id + 1
            gui_label = getattr(self, f"label_lang{gui_id}")
            gui_label_desc = getattr(self, f"label_lang{gui_id}_desc")
            gui_entry = getattr(self, f"entry_lang{gui_id}")
            gui_entry_desc = getattr(self, f"view_lang{gui_id}_desc")
            if lang_id < len(langs):
                # We have this language
                gui_label.set_text(_(langs[lang_id].name_localized) + ":")
                gui_label_desc.set_text(_(langs[lang_id].name_localized) + ":")
            else:
                # We don't.
                gui_label.set_text("")
                gui_entry.set_sensitive(False)
                gui_label_desc.set_text("")
                gui_entry_desc.set_sensitive(False)

    def _init_entid(self):
        name = self._string_provider.get_value(StringType.MOVE_NAMES, self.item_data)
        self.label_id_name.set_text(f"#{self.item_data:04d}: {name}")

    def _init_stores(self):
        self._comboxbox_for_enum(["cb_category"], WazaMoveCategory)
        self._comboxbox_for_enum_with_strings(["cb_type"], PokeType, StringType.TYPE_NAMES)
        self._comboxbox_for_enum(["cb_settings_range_target"], WazaMoveRangeTarget)
        self._comboxbox_for_enum(["cb_settings_range_range"], WazaMoveRangeRange)
        self._comboxbox_for_enum(["cb_settings_range_ai_target"], WazaMoveRangeTarget)
        self._comboxbox_for_enum(["cb_settings_range_ai_range"], WazaMoveRangeRange)
        self._comboxbox_for_enum(["cb_settings_range_ai_condition"], WazaMoveRangeCondition)

    def _init_values(self):
        # Names
        langs = self._string_provider.get_languages()
        for lang_id in range(0, 5):
            gui_id = lang_id + 1
            gui_entry = getattr(self, f"entry_lang{gui_id}")
            gui_entry_desc = getattr(self, f"buff_lang{gui_id}_desc")
            if lang_id < len(langs):
                # We have this language
                gui_entry.set_text(
                    self._string_provider.get_value(StringType.MOVE_NAMES, self.item_data, langs[lang_id])
                )
                gui_entry_desc.set_text(
                    self._string_provider.get_value(StringType.MOVE_DESCRIPTIONS, self.item_data, langs[lang_id])
                )
        self._set_entry("entry_move_id", self.move.move_id)
        self._set_entry("entry_base_power", self.move.base_power)
        self._set_entry("entry_base_pp", self.move.base_pp)
        self._set_entry("entry_accuracy", self.move.accuracy)
        self._set_entry("entry_miss_accuracy", self.move.miss_accuracy)
        self._set_entry("entry_max_upgrade_level", self.move.max_upgrade_level)
        self._set_entry("entry_crit_chance", self.move.crit_chance)
        self._set_entry("entry_number_chained_hits", self.move.number_chained_hits)
        self._set_entry("entry_ai_weight", self.move.ai_weight)
        self._set_entry("entry_ai_condition1_chance", self.move.ai_condition1_chance)
        self._set_entry("entry_range_check_text", self.move.range_check_text)
        self._set_entry("entry_message_id", self.move.message_id)
        self._set_cb("cb_category", self.move.category)
        self._set_cb("cb_type", self.move.type)
        self._set_cb("cb_settings_range_target", self.move.settings_range.target)
        self._set_cb("cb_settings_range_range", self.move.settings_range.range)
        self._set_cb("cb_settings_range_ai_target", self.move.settings_range_ai.target)
        self._set_cb("cb_settings_range_ai_range", self.move.settings_range_ai.range)
        self._set_cb("cb_settings_range_ai_condition", self.move.settings_range_ai.condition)
        self._set_switch("switch_affected_by_magic_coat", self.move.affected_by_magic_coat)
        self._set_switch("switch_is_snatchable", self.move.is_snatchable)
        self._set_switch("switch_uses_mouth", self.move.uses_mouth)
        self._set_switch("switch_ignores_taunted", self.move.ignores_taunted)
        self._set_switch("switch_ai_frozen_check", self.move.ai_frozen_check)

    def mark_as_modified(self):
        if not self._is_loading:
            self.module.mark_move_as_modified(self.item_data)

    def _comboxbox_for_enum(self, names: list[str], enum: type[Enum], sort_by_name=False):
        store = Gtk.ListStore(int, str)  # id, name
        if sort_by_name:
            enum = sorted(enum, key=lambda x: self._enum_entry_to_str(x))  # type: ignore
        for entry in enum:
            store.append([entry.value, self._enum_entry_to_str(entry)])
        for name in names:
            self._fast_set_comboxbox_store(getattr(self, name), store, 1)

    def _comboxbox_for_enum_with_strings(self, names: list[str], enum: type[Enum], string_type: StringType):
        store = Gtk.ListStore(int, str)  # id, name
        for entry in enum:
            store.append([entry.value, self._string_provider.get_value(string_type, entry.value)])
        for name in names:
            self._fast_set_comboxbox_store(getattr(self, name), store, 1)

    @staticmethod
    def _fast_set_comboxbox_store(cb: Gtk.ComboBox, store: Gtk.ListStore, col):
        cb.set_model(store)
        renderer_text = Gtk.CellRendererText()
        cb.pack_start(renderer_text, True)
        cb.add_attribute(renderer_text, "text", col)

    def _enum_entry_to_str(self, entry):
        if hasattr(entry, "print_name"):
            return entry.print_name
        return entry.name.capitalize().replace("_", " ")

    def _set_entry(self, entry_name, text):
        getattr(self, entry_name).set_text(str(text))

    def _set_cb(self, cb_name, value):
        cb = getattr(self, cb_name)
        model = typing.cast(Optional[Gtk.ListStore], cb.get_model())
        assert model is not None
        l_iter = model.get_iter_first()
        while l_iter:
            row = typing.cast(Gtk.ListStore, cb.get_model())[l_iter]
            if row[0] == value:
                cb.set_active_iter(l_iter)
                return
            l_iter = typing.cast(Gtk.ListStore, cb.get_model()).iter_next(l_iter)

    def _set_switch(self, switch_name, value):
        getattr(self, switch_name).set_active(value)

    def _update_from_switch(self, w: Gtk.Switch):
        attr_name = Gtk.Buildable.get_name(w)[7:]
        setattr(self.move, attr_name, w.get_active())

    def _update_from_cb(self, w: Gtk.ComboBox):
        attr_name = Gtk.Buildable.get_name(w)[3:]
        val = w.get_model()[assert_not_none(w.get_active_iter())][0]
        current_val = getattr(self.move, attr_name)
        if isinstance(current_val, Enum):
            enum_class = current_val.__class__
            val = enum_class(val)
        setattr(self.move, attr_name, val)

    def _update_lang_from_entry(self, w: Gtk.Entry, lang_index):
        lang = self._string_provider.get_languages()[lang_index]
        self._string_provider.get_model(lang).strings[
            self._string_provider.get_index(StringType.MOVE_NAMES, self.item_data)
        ] = w.get_text()

    def _update_lang_desc_from_buffer(self, w: Gtk.TextBuffer, lang_index):
        lang = self._string_provider.get_languages()[lang_index]
        self._string_provider.get_model(lang).strings[
            self._string_provider.get_index(StringType.MOVE_DESCRIPTIONS, self.item_data)
        ] = w.get_text(w.get_start_iter(), w.get_end_iter(), False)
