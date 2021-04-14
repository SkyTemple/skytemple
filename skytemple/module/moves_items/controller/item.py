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
from skytemple_files.data.item_s_p.model import ItemSPType
from skytemple_files.data.md.model import PokeType
from skytemple_files.dungeon_data.mappa_bin.item_list import MappaItemCategory


class UseType(Enum):
    USE = 0, _("Use")
    HURL = 1, _("Hurl")
    THROW = 2, _("Throw")
    EQUIP = 3, _("Equip")
    EAT = 4, _("Eat")
    INGEST = 5, _("Ingest")
    PEEL = 6, _("Peel")
    USE7 = 7, _("Use")
    USE8 = 8, _("Use")
    USE9 = 9, _("Use")
    USE10 = 10, _("Use")
    EQUIP11 = 11, _("Equip")
    EQUIP12 = 12, _("Equip")
    USE13 = 13, _("Use")
    USE14 = 14, _("Use")
    USE15 = 15, _("Use")

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    # ignore the first param since it's already set by __new__
    def __init__(
            self, _: str, name_localized: str
    ):
        self.name_localized = name_localized

    def __str__(self):
        return f'UseType.{self.name}'

    def __repr__(self):
        return str(self)

    @property
    def print_name(self):
        return f'{self.value}: {self.name_localized}'


if TYPE_CHECKING:
    from skytemple.module.moves_items.module import MovesItemsModule
logger = logging.getLogger(__name__)


class ItemController(AbstractController):
    def __init__(self, module: 'MovesItemsModule', item_id: int):
        self.module = module
        self.item_id = item_id
        self.item_p, self.item_sp = self.module.get_item(item_id)

        self.builder = None
        self._string_provider = module.project.get_string_provider()

        self._is_loading = True

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'item.glade')

        self._init_language_labels()
        self._init_entid()
        self._init_stores()

        self._is_loading = True
        self._init_values()
        self._is_loading = False

        if not self.item_sp:
            notebook: Gtk.Notebook = self.builder.get_object('main_notebook')
            notebook.remove_page(3)

        self.builder.connect_signals(self)

        return self.builder.get_object('box_main')

    def on_entry_item_id_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_sprite_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_buy_price_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_sell_price_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_palette_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_move_id_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_range_min_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_range_max_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_cb_category_changed(self, w, *args):
        self._update_from_cb(w)
        self.mark_as_modified()

    def on_cb_action_name_changed(self, w, *args):
        self._update_from_cb(w)
        self.mark_as_modified()

    def on_switch_is_valid_state_set(self, w, *args):
        self._update_from_switch(w)
        self.mark_as_modified()

    def on_switch_is_in_td_state_set(self, w, *args):
        self._update_from_switch(w)
        self.mark_as_modified()

    def on_switch_ai_flag_1_state_set(self, w, *args):
        self._update_from_switch(w)
        self.mark_as_modified()

    def on_switch_ai_flag_2_state_set(self, w, *args):
        self._update_from_switch(w)
        self.mark_as_modified()

    def on_switch_ai_flag_3_state_set(self, w, *args):
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

    def on_entry_lang1_short_desc_changed(self, w, *args):
        self._update_lang_short_desc_from_entry(w, 0)
        self.mark_as_modified()

    def on_entry_lang2_short_desc_changed(self, w, *args):
        self._update_lang_short_desc_from_entry(w, 1)
        self.mark_as_modified()

    def on_entry_lang3_short_desc_changed(self, w, *args):
        self._update_lang_short_desc_from_entry(w, 2)
        self.mark_as_modified()

    def on_entry_lang4_short_desc_changed(self, w, *args):
        self._update_lang_short_desc_from_entry(w, 3)
        self.mark_as_modified()

    def on_entry_lang5_short_desc_changed(self, w, *args):
        self._update_lang_short_desc_from_entry(w, 4)
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

    def on_cb_excl_type_changed(self, w, *args):
        val = w.get_model()[w.get_active_iter()][0]
        self.item_sp.type = ItemSPType(val)
        self.mark_as_modified()

    def on_cb_excl_parameter_changed(self, w, *args):
        try:
            val = int(w.get_text())
        except ValueError:
            return
        self.item_sp.parameter = val

    def on_btn_help_range_min_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("For stackable items: Indicates the minimum amount you can get for 1 instance of that item."),
            title=_("Min Amount")
        )
        md.run()
        md.destroy()

    def on_btn_help_range_max_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("For stackable items: Indicates the maximum amount you can get for 1 instance of that item."),
            title=_("Max Amount")
        )
        md.run()
        md.destroy()

    def on_btn_help_move_id_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("The ID of a move, that is associated with this item."),
            title=_("Move ID")
        )
        md.run()
        md.destroy()

    def on_btn_help_excl_parameter_clicked(self, w, *args):
        text = _("Either the ID of a type or of a Pokémon, depending on the type of the exclusive item.\n\n"
                 "IDs for Types:\n")
        for typ in PokeType:
            text += f'{typ.value}: {str(typ)}\n'
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            text,
            title=_("Exclusive Item Parameter")
        )
        md.run()
        md.destroy()

    def on_btn_help_excl_type_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("Some exclusive items are assigned to Pokémon, others to types. See the values in the dropdown for "
              "the possible options."),
            title=_("Exclusive Item Type")
        )
        md.run()
        md.destroy()

    def on_btn_help_action_name_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("Action name displayed in dungeon menus (Use, Eat, Ingest, Equip...).\n"
              "See 'Text Strings' for actual values."),
            title=_("Action Name")
        )
        md.run()
        md.destroy()

    def _init_language_labels(self):
        langs = self._string_provider.get_languages()
        for lang_id in range(0, 5):
            gui_id = lang_id + 1
            gui_label: Gtk.Label = self.builder.get_object(f'label_lang{gui_id}')
            gui_label_desc: Gtk.Label = self.builder.get_object(f'label_lang{gui_id}_desc')
            gui_label_short_desc: Gtk.Label = self.builder.get_object(f'label_lang{gui_id}_short_desc')
            gui_entry: Gtk.Entry = self.builder.get_object(f'entry_lang{gui_id}')
            gui_entry_desc: Gtk.Entry = self.builder.get_object(f'view_lang{gui_id}_desc')
            gui_entry_short_desc: Gtk.Entry = self.builder.get_object(f'entry_lang{gui_id}_short_desc')
            if lang_id < len(langs):
                # We have this language
                gui_label.set_text(_(langs[lang_id].name_localized) + ':')
                gui_label_desc.set_text(_(langs[lang_id].name_localized) + ':')
                gui_label_short_desc.set_text(_(langs[lang_id].name_localized) + ':')
            else:
                # We don't.
                gui_label.set_text("")
                gui_entry.set_sensitive(False)
                gui_label_desc.set_text("")
                gui_entry_desc.set_sensitive(False)
                gui_label_short_desc.set_text("")
                gui_entry_short_desc.set_sensitive(False)

    def _init_entid(self):
        name = self._string_provider.get_value(StringType.ITEM_NAMES, self.item_id)
        self.builder.get_object('label_id_name').set_text(f'#{self.item_id:04d}: {name}')

    def _init_stores(self):
        store = Gtk.ListStore(int, str)  # id, name
        for category in self.module.project.get_rom_module().get_static_data().dungeon_data.item_categories.values():
            store.append([category.id, category.name_localized])
        self._fast_set_comboxbox_store(self.builder.get_object('cb_category'), store, 1)
        self._comboxbox_for_enum(['cb_action_name'], UseType)
        self._comboxbox_for_enum(['cb_excl_type'], ItemSPType)

    def _init_values(self):
        # Names
        langs = self._string_provider.get_languages()
        for lang_id in range(0, 5):
            gui_id = lang_id + 1
            gui_entry: Gtk.Entry = self.builder.get_object(f'entry_lang{gui_id}')
            gui_entry_short_desc: Gtk.Entry = self.builder.get_object(f'entry_lang{gui_id}_short_desc')
            gui_entry_desc: Gtk.TextBuffer = self.builder.get_object(f'buff_lang{gui_id}_desc')
            if lang_id < len(langs):
                # We have this language
                gui_entry.set_text(self._string_provider.get_value(StringType.ITEM_NAMES,
                                                                   self.item_id,
                                                                   langs[lang_id]))
                gui_entry_short_desc.set_text(self._string_provider.get_value(StringType.ITEM_SHORT_DESCRIPTIONS,
                                                                              self.item_id,
                                                                              langs[lang_id]))
                gui_entry_desc.set_text(self._string_provider.get_value(StringType.ITEM_LONG_DESCRIPTIONS,
                                                                        self.item_id,
                                                                        langs[lang_id]))

        self._set_entry('entry_sprite', self.item_p.sprite)
        self._set_entry('entry_palette', self.item_p.palette)
        self._set_entry('entry_item_id', self.item_p.item_id)
        self._set_cb('cb_category', self.item_p.category)
        self._set_entry('entry_buy_price', self.item_p.buy_price)
        self._set_entry('entry_sell_price', self.item_p.sell_price)
        self._set_entry('entry_move_id', self.item_p.move_id)
        self._set_entry('entry_range_min', self.item_p.range_min)
        self._set_entry('entry_range_max', self.item_p.range_max)
        self._set_cb('cb_action_name', self.item_p.action_name)
        self._set_switch('switch_is_valid', self.item_p.is_valid)
        self._set_switch('switch_is_in_td', self.item_p.is_in_td)
        self._set_switch('switch_ai_flag_1', self.item_p.ai_flag_1)
        self._set_switch('switch_ai_flag_2', self.item_p.ai_flag_2)
        self._set_switch('switch_ai_flag_3', self.item_p.ai_flag_3)
        if self.item_sp is not None:
            self._set_cb('cb_excl_type', self.item_sp.type.value)
            self._set_entry('cb_excl_parameter', self.item_sp.parameter)

    def mark_as_modified(self):
        if not self._is_loading:
            self.module.mark_item_as_modified(self.item_id)

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
        setattr(self.item_p, attr_name, val)

    def _update_from_switch(self, w: Gtk.Entry):
        attr_name = Gtk.Buildable.get_name(w)[7:]
        setattr(self.item_p, attr_name, w.get_active())

    def _update_from_cb(self, w: Gtk.ComboBox):
        attr_name = Gtk.Buildable.get_name(w)[3:]
        val = w.get_model()[w.get_active_iter()][0]
        current_val = getattr(self.item_p, attr_name)
        if isinstance(current_val, Enum) and not isinstance(current_val, UseType) and not isinstance(current_val, MappaItemCategory):
            enum_class = current_val.__class__
            val = enum_class(val)
        setattr(self.item_p, attr_name, val)

    def _update_lang_from_entry(self, w: Gtk.Entry, lang_index):
        lang = self._string_provider.get_languages()[lang_index]
        self._string_provider.get_model(lang).strings[
            self._string_provider.get_index(StringType.ITEM_NAMES, self.item_id)
        ] = w.get_text()

    def _update_lang_short_desc_from_entry(self, w: Gtk.Entry, lang_index):
        lang = self._string_provider.get_languages()[lang_index]
        self._string_provider.get_model(lang).strings[
            self._string_provider.get_index(StringType.ITEM_SHORT_DESCRIPTIONS, self.item_id)
        ] = w.get_text()

    def _update_lang_desc_from_buffer(self, w: Gtk.TextBuffer, lang_index):
        lang = self._string_provider.get_languages()[lang_index]
        self._string_provider.get_model(lang).strings[
            self._string_provider.get_index(StringType.ITEM_LONG_DESCRIPTIONS, self.item_id)
        ] = w.get_text(w.get_start_iter(), w.get_end_iter(), False)
