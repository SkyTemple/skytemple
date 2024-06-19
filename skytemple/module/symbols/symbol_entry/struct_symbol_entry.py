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
from skytemple_files.hardcoded.symbols.manual.structs import get_struct_fields
from skytemple_files.hardcoded.symbols.rw_symbol import RWStructSymbol


class StructSymbolEntry(SymbolEntry):
    def __init__(self, rom_project: RomProject, binary_protocol: SectionProtocol, unique_id: int,
            tree_store: Gtk.TreeStore, parent_iter: Optional[Gtk.TreeIter], rw_symbol: RWStructSymbol,
            symbol_entry_list: SymbolEntryList, name_str: str, c_type: CType, desc_str: str, binary_id: str):
        """
        Creates a new struct symbol entry
        :param rw_symbol RWStructSymbol instance for the provided symbol. Must contain all the child RWSymbol instances
        for all elements of the current struct type.
        :param symbol_entry_list SymbolEntryList instance where children of this entry will be stored
        :param name_str String to display as the name of the symbol
        :param c_type C type of this entry. Must be a valid struct type.
        :param desc_str String to display as the description of the symbol
        :param binary_id ID of the binary this symbol belongs to
        :raises ValueError If type_str does not represent a valid struct type
        """
        super().__init__(rom_project, binary_protocol, unique_id, tree_store, parent_iter)

        type_str = str(c_type)

        self._append_to_tree_store(name_str, type_str, desc_str, "", unique_id, binary_id, SymbolEntryValueType.EMPTY)

        # Add child entries
        struct_fields = get_struct_fields(type_str)
        for field in struct_fields:
            child_rw_symbol = rw_symbol.fields[field.name]
            symbol_entry_list.new_entry(name_str + "." + field.name, CType.from_str(field.type), "", child_rw_symbol,
                binary_id, binary_protocol, self.tree_iter)

    @classmethod
    def from_symbol(cls, rom_project: RomProject, binary_protocol: SectionProtocol, unique_id: int,
            tree_store: Gtk.TreeStore, parent_iter: Optional[Gtk.TreeIter], rw_symbol: RWStructSymbol,
            symbol_entry_list: SymbolEntryList, symbol: Symbol, binary_id: str):
        """
        Creates a new struct symbol entry. The name, description and type to display will be pulled from the provided
        Symbol instance.
        """
        return cls(rom_project, binary_protocol, unique_id, tree_store, parent_iter, rw_symbol, symbol_entry_list,
            symbol.name, CType.from_str(symbol.c_type), symbol.description, binary_id)
