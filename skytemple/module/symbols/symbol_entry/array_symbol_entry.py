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
from typing import Optional

from pmdsky_debug_py.protocol import SectionProtocol, Symbol

from gi.repository import Gtk

from skytemple.core.rom_project import RomProject
from skytemple.module.symbols.symbol_entry.symbol_entry import SymbolEntry
from skytemple.module.symbols.symbol_entry.symbol_entry_list import SymbolEntryList
from skytemple.module.symbols.symbol_entry.symbol_entry_value_type import SymbolEntryValueType
from skytemple_files.hardcoded.symbols.c_type import CType
from skytemple_files.hardcoded.symbols.rw_symbol import RWArraySymbol


class ArraySymbolEntry(SymbolEntry):
    def __init__(self, rom_project: RomProject, binary_protocol: SectionProtocol, unique_id: int,
            tree_store: Gtk.TreeStore, parent_iter: Optional[Gtk.TreeIter], rw_symbol: RWArraySymbol,
            symbol_entry_list: SymbolEntryList, name_str: str, c_type: CType, desc_str: str, binary_id: str,
            rw_array_symbol_index: int = 0):
        """
        Creates a new array symbol entry
        :param rw_symbol RWArraySymbol instance for the provided symbol. Must contain all the child RWSymbol instances
        for all elements of the current array type.
        :param symbol_entry_list SymbolEntryList instance where children of this entry will be stored
        :param name_str String to display as the name of the symbol
        :param c_type C type of this entry. Must be a valid array type.
        :param desc_str String to display as the description of the symbol
        :param binary_id ID of the binary this symbol belongs to
        :param rw_array_symbol_index Index in rw_symbol.elements that corresponds to this instance. Needed for
        multi-dimensional arrays.
        :raises ValueError If type_str does not represent a valid array type
        """
        super().__init__(rom_project, binary_protocol, unique_id, tree_store, parent_iter)

        if not c_type.is_array_type():
            raise ValueError("Cannot create array symbol entry from non-array type \"" + str(c_type) + "\"")

        self._append_to_tree_store(name_str, str(c_type), desc_str, "", unique_id, binary_id, SymbolEntryValueType.EMPTY)

        # Add child entries
        child_type = CType.dim_down_array_type(c_type)
        if len(c_type.dim_sizes) == 1:
            # Simple array, create a simple entry for each element
            for i in range(c_type.dim_sizes[0]):
                symbol_entry_list.new_entry(name_str + "[" + str(i) + "]", child_type, "",
                    rw_symbol.elements[rw_array_symbol_index + i], binary_id, binary_protocol, self.tree_iter)
        else:
            # Multi-dimensional array, create an array entry for each element
            for i in range(c_type.dim_sizes[0]):
                child_rw_array_symbol_index = rw_array_symbol_index + child_type.get_total_num_elements() * i
                symbol_entry_list.new_entry(name_str + "[" + str(i) + "]", child_type, "", rw_symbol,
                    binary_id, binary_protocol, self.tree_iter, child_rw_array_symbol_index)

    @classmethod
    def from_symbol(cls, rom_project: RomProject, binary_protocol: SectionProtocol, unique_id: int,
            tree_store: Gtk.TreeStore, parent_iter: Optional[Gtk.TreeIter], rw_symbol: RWArraySymbol,
            symbol_entry_list: SymbolEntryList, symbol: Symbol, binary_id: str):
        """
        Creates a new array symbol entry. The name, description and type to display will be pulled from the provided
        Symbol instance.
        """
        return cls(rom_project, binary_protocol, unique_id, tree_store, parent_iter, rw_symbol, symbol_entry_list,
            symbol.name, CType.from_str(symbol.c_type), symbol.description, binary_id)
