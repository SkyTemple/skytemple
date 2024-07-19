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
from typing import Optional, List

from pmdsky_debug_py.protocol import SectionProtocol
from skytemple.controller.main import MainController
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.rom_project import RomProject
from skytemple.module.symbols.model_getter import ModelGetter
from skytemple.module.symbols.store_entry_value_setter import StoreEntryValueSetter, FONT_WEIGHT_SAVED
from skytemple.module.symbols.symbol_entry.symbol_entry_value_type import SymbolEntryValueType
from skytemple_files.common.rw_value import DATA_PROCESSING_INSTRUCTION_TYPE
from skytemple_files.hardcoded.symbols.c_type import CType
from skytemple_files.hardcoded.symbols.manual.equivalent_types import get_enum_equivalent_type
from skytemple_files.hardcoded.symbols.rw_symbol import RWSymbol, RWSimpleSymbol, RWArraySymbol, RWStructSymbol

# noinspection PyProtectedMember
from skytemple_files.common.i18n_util import _

from gi.repository import Gtk

SHIFTED_IMMEDIATE_DISPLAY_TYPE = "Shifted Immediate"


class SymbolEntry:
    """
    Class used to represent a single entry on the symbol list. It contains enough information to set the required values
    on the UI model, as well as to update the underlying data when a callback takes place.
    """

    rom_project: RomProject

    name: str
    c_type: CType
    description: str

    rw_symbol: RWSymbol
    binary_id: str
    binary_protocol: SectionProtocol

    # The preferred value type for this entry. The entry might end up using a different value if this one cannot
    # be used for some reason.
    value_type: SymbolEntryValueType
    enable_display_type_overrides: bool

    # List of children entries. They will be registered alongside this one when the register() method is called.
    children: List["SymbolEntry"]

    def __init__(
        self,
        rom_project: RomProject,
        name: str,
        c_type: CType,
        description: str,
        rw_symbol: RWSymbol,
        binary_id: str,
        binary_protocol: SectionProtocol,
        value_type: SymbolEntryValueType,
        enable_display_type_overrides: bool,
        children: List["SymbolEntry"],
    ):
        """
        Directly creates an instance of the class by providing all its required data. It is recommended to use a
        SymbolEntryBuilder instead.
        """
        self.rom_project = rom_project
        self.name = name
        self.c_type = c_type
        self.description = description
        self.rw_symbol = rw_symbol
        self.binary_id = binary_id
        self.binary_protocol = binary_protocol
        self.value_type = value_type
        self.enable_display_type_overrides = enable_display_type_overrides
        self.children = children

    def get_str_value(self) -> str:
        """
        :return The current value of this entry pulled from its associated binary, as a string. If the entry is an
        array or a struct, returns an empty string.
        """
        if isinstance(self.rw_symbol, RWSimpleSymbol):
            binary = self.rom_project.get_binary(self.binary_protocol)
            return self.rw_symbol.get_rw_value().read_str(binary)
        elif isinstance(self.rw_symbol, RWArraySymbol):
            return ""
        elif isinstance(self.rw_symbol, RWStructSymbol):
            return ""
        else:
            raise ValueError("Unknown RWSymbol type")

    def register(
        self,
        symbol_entry_list: List["SymbolEntry"],
        tree_store: Gtk.TreeStore,
        parent_iter: Optional[Gtk.TreeIter] = None,
    ):
        """
        Adds this entry to the specified symbol list and to the specified tree store. This will add the entry to the
        UI and assign it a unique ID that can be used to locate it when a callback happens.
        Currently, the ID is simply the index on the symbol list.
        Children entries of this entry will be recursively registered as well.
        :param symbol_entry_list List that contains all the currently registered symbol entries
        :param tree_store Tree store where UI entries are stored
        :param parent_iter If this entry has a parent, TreeIter of the parent entry. None otherwise.
        """
        model_getter = ModelGetter.get_or_create(self.rom_project)

        symbol_entry_list.append(self)
        unique_id = len(symbol_entry_list) - 1

        self._append_to_tree_store(tree_store, model_getter, unique_id, parent_iter)

        for child in self.children:
            child.register(symbol_entry_list, tree_store, self.tree_iter)

    def set_value(self, value: str) -> bool:
        """
        Updates the underlying value of the entry on the corresponding binary. The RWsymbol stored by this instance
        must be a regular symbol (not an array or a struct).
        If the operation raises an error, it is displayed to the user.
        :return True if the value was successfully changed, false otherwise
        :raises ValueError If the RWSymbol contained by this instance is not a RWSimpleSymbol
        """
        if isinstance(self.rw_symbol, RWSimpleSymbol):
            rw_symbol = self.rw_symbol
            try:
                self.rom_project.modify_binary(
                    self.binary_protocol, lambda binary: rw_symbol.get_rw_value().write_str(binary, value)
                )
                return True
            except ValueError as e:
                md = SkyTempleMessageDialog(
                    MainController.window(),
                    Gtk.DialogFlags.DESTROY_WITH_PARENT,
                    Gtk.MessageType.ERROR,
                    Gtk.ButtonsType.OK,
                    _("The value could not be saved: " + str(e)),
                    title=_("Invalid value"),
                )
                md.run()
                md.destroy()
                return False
        else:
            raise ValueError("Cannot set the value of a symbol entry that does not contain a simple symbol.")

    def _append_to_tree_store(
        self, tree_store: Gtk.TreeStore, model_getter: ModelGetter, unique_id: int, parent_iter: Optional[Gtk.TreeIter]
    ):
        """
        Appends this entry to the tree store that contains symbol data
        """

        type_str = str(self.c_type)
        if self.enable_display_type_overrides:
            type_str = self.apply_display_type_overrides()
        type_str = get_enum_equivalent_type(type_str)

        show_value_text = self.value_type == SymbolEntryValueType.TEXT
        show_value_bool = self.value_type == SymbolEntryValueType.BOOLEAN
        show_value_combo = self.value_type == SymbolEntryValueType.DROPDOWN
        show_value_completion = self.value_type == SymbolEntryValueType.COMPLETION

        if self.value_type == SymbolEntryValueType.DROPDOWN or self.value_type == SymbolEntryValueType.COMPLETION:
            model_combo_and_completion = model_getter.get_model(type_str)
        else:
            model_combo_and_completion = None

        # Append new entry. Values are set below.
        self.tree_iter = tree_store.append(
            parent_iter,
            [
                self.name,
                type_str,
                self.description,
                "",
                False,
                "",
                unique_id,
                self.binary_id,
                show_value_text,
                show_value_bool,
                show_value_combo,
                show_value_completion,
                model_combo_and_completion,
                FONT_WEIGHT_SAVED,
            ],
        )

        # Set the value using the designated method to ensure all relevant columns are updated
        store_entry = tree_store[self.tree_iter]
        value = self.get_str_value()
        try:
            StoreEntryValueSetter.set_value(store_entry, value, False)
        except IndexError:
            # This means that the value is out of bounds for the entry's enum type.
            # This can happen if:
            # - A value that is outside of the enum range is used to mark a special entry
            # - The value is modified externally into an out-of-range value
            # - The type of the field specified in pmdsky-debug is incorrect
            # In this case, we just display the cell as text.

            store_entry[8] = True  # show_value_text = True
            store_entry[10] = False  # show_value_combo = False
            store_entry[11] = False  # show_value_completion = False
            store_entry[12] = None  # model_combo_and_completion = None

            # Try again
            StoreEntryValueSetter.set_value(store_entry, value, False)

    def apply_display_type_overrides(self) -> str:
        """
        Applies display type overrides to the type of this entry. Type display overrides simplifies the display of
        some C types to make them easier to understand (for example, "struct data_processing_instruction" gets turned
        into "Shifted Immediate".
        :retrun Type of this entry after applying display type overrides, as a string
        """
        if self.c_type.base_type == DATA_PROCESSING_INSTRUCTION_TYPE:
            # Since we only edit the shifted immediate part of instructions, we use a different display type for these
            return SHIFTED_IMMEDIATE_DISPLAY_TYPE
        else:
            return str(self.c_type)
