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
from typing import List, Optional

from pmdsky_debug_py.protocol import Symbol, SectionProtocol

from gi.repository import Gtk

from skytemple.core.rom_project import RomProject
from skytemple.module.symbols.symbol_entry.simple_symbol_entry import SimpleSymbolEntry
from skytemple.module.symbols.symbol_entry.symbol_entry import SymbolEntry
from skytemple_files.hardcoded.symbols.c_type import CType
from skytemple_files.hardcoded.symbols.rw_symbol import RWSimpleSymbol, RWArraySymbol, RWStructSymbol, RWSymbol


class SymbolEntryList:
    """
    Class used to create and store SymbolEntry instances. Each instance is assigned a unique ID that can be used to
    retrieve it later.
    """

    rom_project: RomProject
    tree_store: Gtk.TreeStore
    entries: List[SymbolEntry | None]
    current_id: int

    def __init__(self, rom_project: RomProject, tree_store: Gtk.TreeStore):
        self.rom_project = rom_project
        self.tree_store = tree_store
        self.entries = []
        self.current_id = 0

    def new_entry(self, name: str, c_type: CType, description: str, rw_symbol: RWSymbol,
            binary_id: str, binary_protocol: SectionProtocol, parent_iter: Optional[Gtk.TreeIter],
            rw_symbol_array_child_index: int = 0) -> SymbolEntry:
        """
        Creates a new entry with the provided data and returns it.
        The exact RWSymbol subclass provided will be used to determine which type of entry is created.
        """

        # We need to determine the ID and allocate a slot on the list before calling the constructor, since some
        # elements create sub-elements.
        new_id = self._get_and_increment_id()
        self.entries.append(None)

        # This needs to be here to avoid a circular import
        from skytemple.module.symbols.symbol_entry.array_symbol_entry import ArraySymbolEntry
        from skytemple.module.symbols.symbol_entry.struct_symbol_entry import StructSymbolEntry
        if isinstance(rw_symbol, RWSimpleSymbol):
            entry = SimpleSymbolEntry(self.rom_project, binary_protocol, new_id, self.tree_store, parent_iter,
                rw_symbol, name, c_type, description, binary_id)
        elif isinstance(rw_symbol, RWArraySymbol):
            entry = ArraySymbolEntry(self.rom_project, binary_protocol, new_id, self.tree_store, parent_iter,
                rw_symbol, self, name, c_type, description, binary_id, rw_symbol_array_child_index)
        elif isinstance(rw_symbol, RWStructSymbol):
            entry = StructSymbolEntry(self.rom_project, binary_protocol, new_id, self.tree_store, parent_iter,
                rw_symbol, self, name, c_type, description, binary_id)
        else:
            raise ValueError("Unknown RWSymbol subtype")

        # Set the entry reference on the list now
        self.entries[new_id] = entry
        return entry

    def new_entry_from_symbol(self, symbol: Symbol, rw_symbol: RWSymbol, binary_id: str,
            binary_protocol: SectionProtocol, parent_iter: Optional[Gtk.TreeIter]) -> SymbolEntry:
        """
        Shorthand for new_entry() that uses a Symbol instance to determine the name, type, and description strings to
        display.
        """
        return self.new_entry(symbol.name, CType.from_str(symbol.c_type), symbol.description, rw_symbol,
            binary_id, binary_protocol, parent_iter)

    def get_by_id(self, unique_id: int) -> SymbolEntry:
        return self.entries[unique_id]

    def clear(self):
        """
        Removes all instances stored in the list. Also resets the internal unique ID counter.
        """
        self.entries.clear()
        self.current_id = 0

    def _get_and_increment_id(self) -> int:
        """
        Returns the value of the current_id field and then increments it by 1
        """
        ret = self.current_id
        self.current_id += 1
        return ret
