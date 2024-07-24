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
from skytemple_files.data.item_s_p.model import ItemSPType
from skytemple_files.data.md.protocol import PokeType
import os

from skytemple.core.widget.sprite import StSprite, StSpriteData
from skytemple.init_locale import LocalePatchedGtkTemplate


class UseType(Enum):
    USE = (0, _("Use"))
    HURL = (1, _("Hurl"))
    THROW = (2, _("Throw"))
    EQUIP = (3, _("Equip"))
    EAT = (4, _("Eat"))
    INGEST = (5, _("Ingest"))
    PEEL = (6, _("Peel"))
    USE7 = (7, _("Use"))
    USE8 = (8, _("Use"))
    USE9 = (9, _("Use"))
    USE10 = (10, _("Use"))
    EQUIP11 = (11, _("Equip"))
    EQUIP12 = (12, _("Equip"))
    USE13 = (13, _("Use"))
    USE14 = (14, _("Use"))
    USE15 = (15, _("Use"))

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    # ignore the first param since it's already set by __new__

    def __init__(self, _: str, name_localized: str):
        self.name_localized = name_localized

    def __str__(self):
        return f"UseType.{self.name}"

    def __repr__(self):
        return str(self)

    @property
    def print_name(self):
        return f"{self.value}: {self.name_localized}"


if TYPE_CHECKING:
    from skytemple.module.moves_items.module import MovesItemsModule
logger = logging.getLogger(__name__)


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "moves_items", "item.ui"))
class StMovesItemsItemPage(Gtk.Box):
    __gtype_name__ = "StMovesItemsItemPage"
    module: MovesItemsModule
    item_data: int
    buff_lang1_desc: Gtk.TextBuffer = cast(Gtk.TextBuffer, Gtk.Template.Child())
    buff_lang2_desc: Gtk.TextBuffer = cast(Gtk.TextBuffer, Gtk.Template.Child())
    buff_lang3_desc: Gtk.TextBuffer = cast(Gtk.TextBuffer, Gtk.Template.Child())
    buff_lang4_desc: Gtk.TextBuffer = cast(Gtk.TextBuffer, Gtk.Template.Child())
    buff_lang5_desc: Gtk.TextBuffer = cast(Gtk.TextBuffer, Gtk.Template.Child())
    label_id_name: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    entry_item_id: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    cb_category: Gtk.ComboBox = cast(Gtk.ComboBox, Gtk.Template.Child())
    entry_sprite: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_buy_price: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_sell_price: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_palette: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    sprite_container: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    main_notebook: Gtk.Notebook = cast(Gtk.Notebook, Gtk.Template.Child())
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
    label_lang1_short_desc: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    label_lang2_short_desc: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    label_lang3_short_desc: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    label_lang4_short_desc: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    label_lang5_short_desc: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    entry_lang1_short_desc: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_lang2_short_desc: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_lang3_short_desc: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_lang4_short_desc: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_lang5_short_desc: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_move_id: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_range_min: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    btn_help_range_min: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    entry_range_max: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    btn_help_range_max: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    btn_help_move_id: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    cb_action_name: Gtk.ComboBox = cast(Gtk.ComboBox, Gtk.Template.Child())
    btn_help_action_name: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    switch_is_valid: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    switch_is_in_td: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    switch_ai_flag_1: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    switch_ai_flag_2: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    switch_ai_flag_3: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    cb_excl_parameter: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    btn_help_excl_parameter: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    btn_help_excl_type: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    cb_excl_type: Gtk.ComboBox = cast(Gtk.ComboBox, Gtk.Template.Child())
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
        self.item_p, self.item_sp = self.module.get_item(item_data)
        self._string_provider = module.project.get_string_provider()
        self._sprite_provider = module.project.get_sprite_provider()
        self._is_loading = True
        self._init_language_labels()
        self._init_entid()
        self._init_stores()
        self._is_loading = True
        self._init_values()
        self._is_loading = False
        if not self.item_sp:
            notebook = self.main_notebook
            notebook.remove_page(3)

        self._reset_sprite()

    @Gtk.Template.Callback()
    @catch_overflow(u16)
    def on_entry_item_id_changed(self, w, *args):
        try:
            val = u16_checked(int(w.get_text()))
        except ValueError:
            return
        self.item_p.item_id = val
        self.mark_as_modified()

    @Gtk.Template.Callback()
    @catch_overflow(u8)
    def on_entry_sprite_changed(self, w, *args):
        try:
            val = u8_checked(int(w.get_text()))
        except ValueError:
            return
        self.item_p.sprite = val
        self.mark_as_modified()
        self._sprite_provider.reset()
        self._reset_sprite()

    @Gtk.Template.Callback()
    @catch_overflow(u16)
    def on_entry_buy_price_changed(self, w, *args):
        try:
            val = u16_checked(int(w.get_text()))
        except ValueError:
            return
        self.item_p.buy_price = val
        self.mark_as_modified()

    @Gtk.Template.Callback()
    @catch_overflow(u16)
    def on_entry_sell_price_changed(self, w, *args):
        try:
            val = u16_checked(int(w.get_text()))
        except ValueError:
            return
        self.item_p.sell_price = val
        self.mark_as_modified()

    @Gtk.Template.Callback()
    @catch_overflow(u8)
    def on_entry_palette_changed(self, w, *args):
        try:
            val = u8_checked(int(w.get_text()))
        except ValueError:
            return
        self.item_p.palette = val
        self.mark_as_modified()
        self._sprite_provider.reset()
        self._reset_sprite()

    @Gtk.Template.Callback()
    @catch_overflow(u16)
    def on_entry_move_id_changed(self, w, *args):
        try:
            val = u16_checked(int(w.get_text()))
        except ValueError:
            return
        self.item_p.move_id = val
        self.mark_as_modified()

    @Gtk.Template.Callback()
    @catch_overflow(u8)
    def on_entry_range_min_changed(self, w, *args):
        try:
            val = u8_checked(int(w.get_text()))
        except ValueError:
            return
        self.item_p.range_min = val
        self.mark_as_modified()

    @Gtk.Template.Callback()
    @catch_overflow(u8)
    def on_entry_range_max_changed(self, w, *args):
        try:
            val = u8_checked(int(w.get_text()))
        except ValueError:
            return
        self.item_p.range_max = val
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_cb_category_changed(self, w, *args):
        self._update_from_cb(w)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_cb_action_name_changed(self, w, *args):
        self._update_from_cb(w)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_switch_is_valid_state_set(self, w, *args):
        self._update_from_switch(w)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_switch_is_in_td_state_set(self, w, *args):
        self._update_from_switch(w)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_switch_ai_flag_1_state_set(self, w, *args):
        self._update_from_switch(w)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_switch_ai_flag_2_state_set(self, w, *args):
        self._update_from_switch(w)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_switch_ai_flag_3_state_set(self, w, *args):
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
    def on_entry_lang1_short_desc_changed(self, w, *args):
        self._update_lang_short_desc_from_entry(w, 0)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_entry_lang2_short_desc_changed(self, w, *args):
        self._update_lang_short_desc_from_entry(w, 1)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_entry_lang3_short_desc_changed(self, w, *args):
        self._update_lang_short_desc_from_entry(w, 2)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_entry_lang4_short_desc_changed(self, w, *args):
        self._update_lang_short_desc_from_entry(w, 3)
        self.mark_as_modified()

    @Gtk.Template.Callback()
    def on_entry_lang5_short_desc_changed(self, w, *args):
        self._update_lang_short_desc_from_entry(w, 4)
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
    def on_cb_excl_type_changed(self, w, *args):
        val = w.get_model()[w.get_active_iter()][0]
        self.item_sp.type = ItemSPType(val)  # type: ignore
        self.mark_as_modified()

    @Gtk.Template.Callback()
    @catch_overflow(u16)
    def on_cb_excl_parameter_changed(self, w, *args):
        try:
            val = u16_checked(int(w.get_text()))
        except ValueError:
            return
        assert self.item_sp is not None
        self.item_sp.parameter = val

    @Gtk.Template.Callback()
    def on_btn_help_range_min_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("For stackable items: Indicates the minimum amount you can get for 1 instance of that item."),
            title=_("Min Amount"),
        )
        md.run()
        md.destroy()

    @Gtk.Template.Callback()
    def on_btn_help_range_max_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("For stackable items: Indicates the maximum amount you can get for 1 instance of that item."),
            title=_("Max Amount"),
        )
        md.run()
        md.destroy()

    @Gtk.Template.Callback()
    def on_btn_help_move_id_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("The ID of a move, that is associated with this item."),
            title=_("Move ID"),
        )
        md.run()
        md.destroy()

    @Gtk.Template.Callback()
    def on_btn_help_excl_parameter_clicked(self, w, *args):
        text = _(
            "Either the ID of a type or of a Pokémon, depending on the type of the exclusive item.\n\nIDs for Types:\n"
        )
        for typ in PokeType:
            text += f"{typ.value}: {self._string_provider.get_value(StringType.TYPE_NAMES, typ.value)}\n"
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            text,
            title=_("Exclusive Item Parameter"),
        )
        md.run()
        md.destroy()

    @Gtk.Template.Callback()
    def on_btn_help_excl_type_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _(
                "Some exclusive items are assigned to Pokémon, others to types. See the values in the dropdown for the possible options."
            ),
            title=_("Exclusive Item Type"),
        )
        md.run()
        md.destroy()

    @Gtk.Template.Callback()
    def on_btn_help_action_name_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _(
                "Action name displayed in dungeon menus (Use, Eat, Ingest, Equip...).\nSee 'Text Strings' for actual values."
            ),
            title=_("Action Name"),
        )
        md.run()
        md.destroy()

    def _init_language_labels(self):
        langs = self._string_provider.get_languages()
        for lang_id in range(0, 5):
            gui_id = lang_id + 1
            gui_label = getattr(self, f"label_lang{gui_id}")
            gui_label_desc = getattr(self, f"label_lang{gui_id}_desc")
            gui_label_short_desc = getattr(self, f"label_lang{gui_id}_short_desc")
            gui_entry = getattr(self, f"entry_lang{gui_id}")
            gui_entry_desc = getattr(self, f"view_lang{gui_id}_desc")
            gui_entry_short_desc = getattr(self, f"entry_lang{gui_id}_short_desc")
            if lang_id < len(langs):
                # We have this language
                gui_label.set_text(_(langs[lang_id].name_localized) + ":")
                gui_label_desc.set_text(_(langs[lang_id].name_localized) + ":")
                gui_label_short_desc.set_text(_(langs[lang_id].name_localized) + ":")
            else:
                # We don't.
                gui_label.set_text("")
                gui_entry.set_sensitive(False)
                gui_label_desc.set_text("")
                gui_entry_desc.set_sensitive(False)
                gui_label_short_desc.set_text("")
                gui_entry_short_desc.set_sensitive(False)

    def _init_entid(self):
        name = self._string_provider.get_value(StringType.ITEM_NAMES, self.item_data)
        self.label_id_name.set_text(f"#{self.item_data:04d}: {name}")

    def _init_stores(self):
        store = Gtk.ListStore(int, str)  # id, name
        for category in self.module.project.get_rom_module().get_static_data().dungeon_data.item_categories.values():
            store.append([category.id, category.name_localized])
        self._fast_set_comboxbox_store(self.cb_category, store, 1)
        self._comboxbox_for_enum(["cb_action_name"], UseType)
        self._comboxbox_for_enum(["cb_excl_type"], ItemSPType)

    def _init_values(self):
        # Names
        langs = self._string_provider.get_languages()
        for lang_id in range(0, 5):
            gui_id = lang_id + 1
            gui_entry = getattr(self, f"entry_lang{gui_id}")
            gui_entry_short_desc = getattr(self, f"entry_lang{gui_id}_short_desc")
            gui_entry_desc = getattr(self, f"buff_lang{gui_id}_desc")
            if lang_id < len(langs):
                # We have this language
                gui_entry.set_text(
                    self._string_provider.get_value(StringType.ITEM_NAMES, self.item_data, langs[lang_id])
                )
                gui_entry_short_desc.set_text(
                    self._string_provider.get_value(
                        StringType.ITEM_SHORT_DESCRIPTIONS,
                        self.item_data,
                        langs[lang_id],
                    )
                )
                gui_entry_desc.set_text(
                    self._string_provider.get_value(
                        StringType.ITEM_LONG_DESCRIPTIONS,
                        self.item_data,
                        langs[lang_id],
                    )
                )
        self._set_entry("entry_sprite", self.item_p.sprite)
        self._set_entry("entry_palette", self.item_p.palette)
        self._set_entry("entry_item_id", self.item_p.item_id)
        self._set_cb("cb_category", self.item_p.category)
        self._set_entry("entry_buy_price", self.item_p.buy_price)
        self._set_entry("entry_sell_price", self.item_p.sell_price)
        self._set_entry("entry_move_id", self.item_p.move_id)
        self._set_entry("entry_range_min", self.item_p.range_min)
        self._set_entry("entry_range_max", self.item_p.range_max)
        self._set_cb("cb_action_name", self.item_p.action_name)
        self._set_switch("switch_is_valid", self.item_p.is_valid)
        self._set_switch("switch_is_in_td", self.item_p.is_in_td)
        self._set_switch("switch_ai_flag_1", self.item_p.ai_flag_1)
        self._set_switch("switch_ai_flag_2", self.item_p.ai_flag_2)
        self._set_switch("switch_ai_flag_3", self.item_p.ai_flag_3)
        if self.item_sp is not None:
            self._set_cb("cb_excl_type", self.item_sp.type.value)
            self._set_entry("cb_excl_parameter", self.item_sp.parameter)

    def mark_as_modified(self):
        if not self._is_loading:
            self.module.mark_item_as_modified(self.item_data)

    def _comboxbox_for_enum(self, names: list[str], enum: type[Enum], sort_by_name=False):
        store = Gtk.ListStore(int, str)  # id, name
        if sort_by_name:
            enum = sorted(enum, key=lambda x: self._enum_entry_to_str(x))  # type: ignore
        for entry in enum:
            store.append([entry.value, self._enum_entry_to_str(entry)])
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
        setattr(self.item_p, attr_name, w.get_active())

    def _update_from_cb(self, w: Gtk.ComboBox):
        attr_name = Gtk.Buildable.get_name(w)[3:]
        val = w.get_model()[assert_not_none(w.get_active_iter())][0]
        current_val = getattr(self.item_p, attr_name)
        if isinstance(current_val, Enum):
            enum_class = current_val.__class__
            val = enum_class(val)
        setattr(self.item_p, attr_name, val)

    def _update_lang_from_entry(self, w: Gtk.Entry, lang_index):
        lang = self._string_provider.get_languages()[lang_index]
        self._string_provider.get_model(lang).strings[
            self._string_provider.get_index(StringType.ITEM_NAMES, self.item_data)
        ] = w.get_text()

    def _update_lang_short_desc_from_entry(self, w: Gtk.Entry, lang_index):
        lang = self._string_provider.get_languages()[lang_index]
        self._string_provider.get_model(lang).strings[
            self._string_provider.get_index(StringType.ITEM_SHORT_DESCRIPTIONS, self.item_data)
        ] = w.get_text()

    def _update_lang_desc_from_buffer(self, w: Gtk.TextBuffer, lang_index):
        lang = self._string_provider.get_languages()[lang_index]
        self._string_provider.get_model(lang).strings[
            self._string_provider.get_index(StringType.ITEM_LONG_DESCRIPTIONS, self.item_data)
        ] = w.get_text(w.get_start_iter(), w.get_end_iter(), False)

    def _reset_sprite(self):
        for child in self.sprite_container.get_children():
            self.sprite_container.remove(child)

        sp = StSprite(StSpriteData(self._sprite_provider.get_for_item, (self.item_p,), scale=2))
        self.sprite_container.add(sp)
        sp.show()
