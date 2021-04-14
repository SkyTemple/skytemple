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
from enum import Enum
from typing import TYPE_CHECKING, Type, List

from gi.repository import Gtk

from skytemple.controller.main import MainController
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.module_controller import AbstractController
from skytemple.core.string_provider import StringType
from skytemple_files.common.i18n_util import _
from skytemple_files.data.md.model import PokeType
from skytemple_files.data.waza_p.model import WazaMoveCategory, WazaMoveRangeTarget, WazaMoveRangeRange, \
    WazaMoveRangeCondition


if TYPE_CHECKING:
    from skytemple.module.moves_items.module import MovesItemsModule
logger = logging.getLogger(__name__)


class MoveController(AbstractController):
    def __init__(self, module: 'MovesItemsModule', move_id: int):
        self.module = module
        self.move_id = move_id
        self.move = self.module.get_move(move_id)

        self.builder = None
        self._string_provider = module.project.get_string_provider()

        self._is_loading = True

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'move.glade')

        self._init_language_labels()
        self._init_entid()
        self._init_stores()

        self._is_loading = True
        self._init_values()
        self._is_loading = False

        self.builder.connect_signals(self)

        return self.builder.get_object('box_main')

    def on_entry_move_id_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_base_power_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_base_pp_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_accuracy_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_miss_accuracy_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_max_upgrade_level_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_crit_chance_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_number_chained_hits_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_ai_weight_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_ai_condition1_chance_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_unk13_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_unk15_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_message_id_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_cb_type_changed(self, w, *args):
        self._update_from_cb(w)
        self.mark_as_modified()

    def on_cb_category_changed(self, w, *args):
        self._update_from_cb(w)
        self.mark_as_modified()

    def on_cb_settings_range_range_changed(self, w, *args):
        val = w.get_model()[w.get_active_iter()][0]
        self.move.settings_range.range = WazaMoveRangeRange(val)
        self.mark_as_modified()

    def on_cb_settings_range_target_changed(self, w, *args):
        val = w.get_model()[w.get_active_iter()][0]
        self.move.settings_range.target = WazaMoveRangeTarget(val)
        self.mark_as_modified()

    def on_cb_settings_range_ai_target_changed(self, w, *args):
        val = w.get_model()[w.get_active_iter()][0]
        self.move.settings_range_ai.target = WazaMoveRangeTarget(val)
        self.mark_as_modified()

    def on_cb_settings_range_ai_range_changed(self, w, *args):
        val = w.get_model()[w.get_active_iter()][0]
        self.move.settings_range_ai.range = WazaMoveRangeRange(val)
        self.mark_as_modified()

    def on_cb_settings_range_ai_condition_changed(self, w, *args):
        val = w.get_model()[w.get_active_iter()][0]
        self.move.settings_range_ai.condition = WazaMoveRangeCondition(val)
        self.mark_as_modified()

    def on_switch_affected_by_magic_coat_state_set(self, w, *args):
        self._update_from_switch(w)
        self.mark_as_modified()

    def on_switch_is_snatchable_state_set(self, w, *args):
        self._update_from_switch(w)
        self.mark_as_modified()

    def on_switch_uses_mouth_state_set(self, w, *args):
        self._update_from_switch(w)
        self.mark_as_modified()

    def on_switch_ignores_taunted_state_set(self, w, *args):
        self._update_from_switch(w)
        self.mark_as_modified()

    def on_entry_lang1_changed(self, w, *args):
        # TODO: Update name in tree
        self._update_lang_from_entry(w, 0)
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

    def on_buff_lang1_desc_changed(self, w, *args):
        self._update_lang_desc_from_buffer(w, 0)
        self.mark_as_modified()

    def on_buff_lang2_desc_changed(self, w, *args):
        self._update_lang_desc_from_buffer(w, 1)
        self.mark_as_modified()

    def on_buff_lang3_desc_changed(self, w, *args):
        self._update_lang_desc_from_buffer(w, 2)
        self.mark_as_modified()

    def on_buff_lang4_desc_changed(self, w, *args):
        self._update_lang_desc_from_buffer(w, 3)
        self.mark_as_modified()

    def on_buff_lang5_desc_changed(self, w, *args):
        self._update_lang_desc_from_buffer(w, 4)
        self.mark_as_modified()

    def on_btn_help_accuracy_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("The percentage indicating the chances the move will succeed. "
              "100 is perfect accuracy. Anything higher than 100 is a never-miss move."),
            title=_("Accuracy:")[:-1]
        )
        md.run()
        md.destroy()

    def on_btn_help_miss_accuracy_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("Seems to be a second sort of accuracy check. "
              "A different message will be shown if this accuracy test fails."),
            title=_("Miss Accuracy:")[:-1]
        )
        md.run()
        md.destroy()

    def on_btn_help_number_chained_hits_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("Possibly the number of times a move hits in a row."),
            title=_("# of chained hits:")[:-1]
        )
        md.run()
        md.destroy()

    def on_btn_help_settings_range_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("These are the range settings that the game uses for processing the actual move."),
            title=_("Actual values:")[:-1]
        )
        md.run()
        md.destroy()

    def on_btn_help_settings_range_ai_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("When deciding what move to use, the AI will treat the move like it actually has the range settings "
              "configured here.") + _('\nDue to a bug, if the values are "straight line", "In front; cuts corners" or '
                                      '"Two tiles away; cuts corners" are chosen here, the AI range is used as the '
                                      'ACTUAL range of the move.'),
            title=_("Values used for AI calculation:")[:-1]
        )
        md.run()
        md.destroy()

    def on_btn_help_settings_range_ai_condition_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("The Pokémon must be in this condition in order for this move to be used."),
            title=_("Required condition:")[:-1]
        )
        md.run()
        md.destroy()

    def on_btn_help_affected_by_magic_coat_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("Whether the move is affected by magic coat."),
            title=_("Affected by Magic Coat:")[:-1]
        )
        md.run()
        md.destroy()

    def on_btn_help_is_snatchable_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("Whether the move is affected by snatch."),
            title=_("Is Snatchable:")[:-1]
        )
        md.run()
        md.destroy()

    def on_btn_help_uses_mouth_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _('Whether the move is disabled by the "muzzled" status.'),
            title=_("Uses Mouth:")[:-1]
        )
        md.run()
        md.destroy()

    def on_btn_help_ignores_taunted_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("Whether the move can be used while taunted."),
            title=_("Ignores Taunted:")[:-1]
        )
        md.run()
        md.destroy()

    def on_btn_help_message_id_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("Message ID offset that is displayed for the move. 0 uses the Text String 3860. Higher values select "
              "the strings after that (offsets)."),
            title=_("Message ID:")[:-1]
        )
        md.run()
        md.destroy()

    def _init_language_labels(self):
        langs = self._string_provider.get_languages()
        for lang_id in range(0, 5):
            gui_id = lang_id + 1
            gui_label: Gtk.Label = self.builder.get_object(f'label_lang{gui_id}')
            gui_label_desc: Gtk.Label = self.builder.get_object(f'label_lang{gui_id}_desc')
            gui_entry: Gtk.Entry = self.builder.get_object(f'entry_lang{gui_id}')
            gui_entry_desc: Gtk.Entry = self.builder.get_object(f'view_lang{gui_id}_desc')
            if lang_id < len(langs):
                # We have this language
                gui_label.set_text(_(langs[lang_id].name_localized) + ':')
                gui_label_desc.set_text(_(langs[lang_id].name_localized) + ':')
            else:
                # We don't.
                gui_label.set_text("")
                gui_entry.set_sensitive(False)
                gui_label_desc.set_text("")
                gui_entry_desc.set_sensitive(False)

    def _init_entid(self):
        name = self._string_provider.get_value(StringType.MOVE_NAMES, self.move_id)
        self.builder.get_object('label_id_name').set_text(f'#{self.move_id:04d}: {name}')

    def _init_stores(self):
        self._comboxbox_for_enum(['cb_category'], WazaMoveCategory)
        self._comboxbox_for_enum(['cb_type'], PokeType)
        self._comboxbox_for_enum(['cb_settings_range_target'], WazaMoveRangeTarget)
        self._comboxbox_for_enum(['cb_settings_range_range'], WazaMoveRangeRange)
        self._comboxbox_for_enum(['cb_settings_range_ai_target'], WazaMoveRangeTarget)
        self._comboxbox_for_enum(['cb_settings_range_ai_range'], WazaMoveRangeRange)
        self._comboxbox_for_enum(['cb_settings_range_ai_condition'], WazaMoveRangeCondition)

    def _init_values(self):
        # Names
        langs = self._string_provider.get_languages()
        for lang_id in range(0, 5):
            gui_id = lang_id + 1
            gui_entry: Gtk.Entry = self.builder.get_object(f'entry_lang{gui_id}')
            gui_entry_desc: Gtk.TextBuffer = self.builder.get_object(f'buff_lang{gui_id}_desc')
            if lang_id < len(langs):
                # We have this language
                gui_entry.set_text(self._string_provider.get_value(StringType.MOVE_NAMES,
                                                                   self.move_id,
                                                                   langs[lang_id]))
                gui_entry_desc.set_text(self._string_provider.get_value(StringType.MOVE_DESCRIPTIONS,
                                                                        self.move_id,
                                                                        langs[lang_id]))

        self._set_entry('entry_move_id', self.move.move_id)
        self._set_entry('entry_base_power', self.move.base_power)
        self._set_entry('entry_base_pp', self.move.base_pp)
        self._set_entry('entry_accuracy', self.move.accuracy)
        self._set_entry('entry_miss_accuracy', self.move.miss_accuracy)
        self._set_entry('entry_max_upgrade_level', self.move.max_upgrade_level)
        self._set_entry('entry_crit_chance', self.move.crit_chance)
        self._set_entry('entry_number_chained_hits', self.move.number_chained_hits)
        self._set_entry('entry_ai_weight', self.move.ai_weight)
        self._set_entry('entry_ai_condition1_chance', self.move.ai_condition1_chance)
        self._set_entry('entry_unk13', self.move.unk13)
        self._set_entry('entry_unk15', self.move.unk15)
        self._set_entry('entry_message_id', self.move.message_id)

        self._set_cb('cb_category', self.move.category.value)
        self._set_cb('cb_type', self.move.type.value)
        self._set_cb('cb_settings_range_target', self.move.settings_range.target.value)
        self._set_cb('cb_settings_range_range', self.move.settings_range.range.value)
        self._set_cb('cb_settings_range_ai_target', self.move.settings_range_ai.target.value)
        self._set_cb('cb_settings_range_ai_range', self.move.settings_range_ai.range.value)
        self._set_cb('cb_settings_range_ai_condition', self.move.settings_range_ai.condition.value)

        self._set_switch('switch_affected_by_magic_coat', self.move.affected_by_magic_coat)
        self._set_switch('switch_is_snatchable', self.move.is_snatchable)
        self._set_switch('switch_uses_mouth', self.move.uses_mouth)
        self._set_switch('switch_ignores_taunted', self.move.ignores_taunted)

    def mark_as_modified(self):
        if not self._is_loading:
            self.module.mark_move_as_modified(self.move_id)

    def _comboxbox_for_enum(self, names: List[str], enum: Type[Enum], sort_by_name=False):
        store = Gtk.ListStore(int, str)  # id, name
        if sort_by_name:
            enum = sorted(enum, key=lambda x: self._enum_entry_to_str(x))
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
        setattr(self.move, attr_name, val)

    def _update_from_switch(self, w: Gtk.Entry):
        attr_name = Gtk.Buildable.get_name(w)[7:]
        setattr(self.move, attr_name, w.get_active())

    def _update_from_cb(self, w: Gtk.ComboBox):
        attr_name = Gtk.Buildable.get_name(w)[3:]
        val = w.get_model()[w.get_active_iter()][0]
        current_val = getattr(self.move, attr_name)
        if isinstance(current_val, Enum):
            enum_class = current_val.__class__
            val = enum_class(val)
        setattr(self.move, attr_name, val)

    def _update_lang_from_entry(self, w: Gtk.Entry, lang_index):
        lang = self._string_provider.get_languages()[lang_index]
        self._string_provider.get_model(lang).strings[
            self._string_provider.get_index(StringType.MOVE_NAMES, self.move_id)
        ] = w.get_text()

    def _update_lang_desc_from_buffer(self, w: Gtk.TextBuffer, lang_index):
        lang = self._string_provider.get_languages()[lang_index]
        self._string_provider.get_model(lang).strings[
            self._string_provider.get_index(StringType.MOVE_DESCRIPTIONS, self.move_id)
        ] = w.get_text(w.get_start_iter(), w.get_end_iter(), False)
