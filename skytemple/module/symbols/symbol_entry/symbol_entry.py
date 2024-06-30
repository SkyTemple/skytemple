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
from abc import ABC
from typing import Optional

from pmdsky_debug_py.protocol import SectionProtocol

from gi.repository import Gtk

from skytemple.core.rom_project import RomProject
from skytemple.module.symbols.model_getter import ModelGetter
from skytemple.module.symbols.store_entry_value_setter import StoreEntryValueSetter
from skytemple.module.symbols.symbol_entry.symbol_entry_value_type import SymbolEntryValueType


class SymbolEntry(ABC):
    """
    Class used to represent a single entry on the symbol list. It's responsible for setting the required values
    on the UI model when created, as well as updating the underlying data when a callback takes place.
    """

    rom_project: RomProject
    binary_protocol: SectionProtocol
    # Unique identifier for this instance. Needed as a workaround, since it doesn't look like Gtk allows storing
    # references to objects in TreStore instances.
    unique_id: int

    model_getter: ModelGetter

    # - UI elements -
    # The TreeStore used to hold the data linked to the UI
    tree_store: Gtk.TreeStore
    # The TreeIter that points to the data row that corresponds to this entry
    tree_iter: Gtk.TreeIter
    # The TreeIter that points to the data row that corresponds to the parent of this entry, or None if this is a
    # root entry in the tree.
    parent_iter: Optional[Gtk.TreeIter]

    def __init__(self, rom_project: RomProject, binary_protocol: SectionProtocol, unique_id: int,
            tree_store: Gtk.TreeStore, parent_iter: Optional[Gtk.TreeIter]):
        """
        Creates a new symbol entry. The provided TreeStore will have a new entry added to it. Its corresponding
        UI element will be modified as needed by this entry.
        :param rom_project Current ROM project
        :param binary_protocol Protocol for the binary where the provided symbol is located
        :param unique_id Unique ID value for this instance. Must be different than the value passed to any other
        instances of this class.
        :param tree_store TreeStore that contains the underlying data for the symbol entry
        :param parent_iter TreeIter that points to the data row that corresponds to the parent of this entry, or None
        if this is a root entry in the tree.
        """
        self.rom_project = rom_project
        self.binary_protocol = binary_protocol
        self.unique_id = unique_id

        self.model_getter = ModelGetter.get_or_create(self.rom_project)

        self.tree_store = tree_store
        self.parent_iter = parent_iter

    def _append_to_tree_store(self, symbol_name: str, type_str: str, description: str, value: str,
            unique_id: int, binary_id: str, value_type: SymbolEntryValueType):
        """
        Appends a new entry to the tree store that contains symbol data. Should be called by the subclasses at the
        end of their constructors.
        :param symbol_name Display name
        :param type_str Display type
        :param description Description to show
        :param value Value to show
        :param unique_id Unique ID for this entry
        :param binary_id ID of the binary this symbol belongs to
        :param value_type Type of value cell to display
        """

        show_value_text = value_type == SymbolEntryValueType.TEXT
        show_value_bool = value_type == SymbolEntryValueType.BOOLEAN
        show_value_combo = value_type == SymbolEntryValueType.DROPDOWN
        show_value_completion = value_type == SymbolEntryValueType.COMPLETION

        if value_type == SymbolEntryValueType.DROPDOWN or value_type == SymbolEntryValueType.COMPLETION:
            model_combo_and_completion = self.model_getter.get_model(type_str)
        else:
            model_combo_and_completion = None

        # Append new entry. The value is set below.
        self.tree_iter = self.tree_store.append(self.parent_iter, [symbol_name, type_str, description, "",
            False, "", unique_id, binary_id, show_value_text, show_value_bool, show_value_combo, show_value_completion,
            model_combo_and_completion])

        # Set the value using the designated method to ensure all relevant columns are updated
        store_entry = self.tree_store[self.tree_iter]
        try:
            StoreEntryValueSetter.set_value(store_entry, value)
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
            StoreEntryValueSetter.set_value(store_entry, value)
