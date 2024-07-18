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

from pmdsky_debug_py.protocol import SectionProtocol, Symbol
from skytemple.core.rom_project import RomProject
from skytemple.module.symbols.symbol_entry.symbol_entry import SymbolEntry
from skytemple.module.symbols.symbol_entry.symbol_entry_value_type import SymbolEntryValueType
from skytemple_files.hardcoded.symbols.c_type import CType
from skytemple_files.hardcoded.symbols.manual.equivalent_types import get_enum_equivalent_type
from skytemple_files.hardcoded.symbols.manual.structs import get_struct_fields
from skytemple_files.hardcoded.symbols.rw_symbol import RWSymbol, RWSimpleSymbol, RWArraySymbol, RWStructSymbol


class SymbolEntryBuilder:
    """
    Class used to create SymbolEntry instances. It supports multiple ways of creating them, as well as some
    pre-creation operations that will affect the data that goes into the final object.
    """

    _rom_project: Optional[RomProject]
    _name: str
    _c_type: Optional[CType]
    _description: str
    _rw_symbol: Optional[RWSymbol]
    _binary_id: str
    _binary_protocol: Optional[SectionProtocol]
    _enable_display_type_overrides: bool

    # Index in rw_symbol.elements that corresponds to this instance. Only needed for multi-dimensional arrays.
    _rw_array_symbol_index: int

    def __init__(self):
        """
        Creates a new builder. Default values will be set for all fields. Keep in mind that certain fields must be
        initialized before the build() method can be called.
        """
        self._rom_project = None
        self._name = ""
        self._c_type = None
        self._description = ""
        self._rw_symbol = None
        self._binary_id = ""
        self._binary_protocol = None
        self._enable_display_type_overrides = True

        self._rw_array_symbol_index = 0

    def set_rom_project(self, rom_project: RomProject) -> SymbolEntryBuilder:
        """
        Sets the ROM project used to retrieve ROM data
        """
        self._rom_project = rom_project
        return self

    def set_name(self, name: str) -> SymbolEntryBuilder:
        """
        Sets the disaplay name of the entry
        """
        self._name = name
        return self

    def set_c_type(self, c_type: CType) -> SymbolEntryBuilder:
        """
        Sets the C tpye of the entry. The type is used to determine the type string to show, as well as to determine
        which child elements to create.
        """
        self._c_type = c_type
        return self

    def set_description(self, description: str) -> SymbolEntryBuilder:
        """
        Sets the display description of the entry
        """
        self._description = description
        return self

    def set_name_type_desc_from_symbol(self, symbol: Symbol) -> SymbolEntryBuilder:
        """
        Sets the name, type, and description of this entry with data from the given symbol
        :raises ValueError If the provided symbol has no type
        """
        if symbol.c_type is None:
            raise ValueError("Cannot create a symbol entry from a symbol with no type")
        else:
            self._name = symbol.name
            self._c_type = CType.from_str(symbol.c_type)
            self._description = symbol.description
        return self

    def set_rw_data(self, rw_symbol: RWSymbol, binary_id: str, binary_protocol: SectionProtocol) -> SymbolEntryBuilder:
        """
        Sets the values that will allow the resulting symbol entry to read and write its value to its corresponding
        binary.
        """
        self._rw_symbol = rw_symbol
        self._binary_id = binary_id
        self._binary_protocol = binary_protocol
        return self

    def enable_display_type_overrides(self, enable: bool) -> SymbolEntryBuilder:
        """
        Sets whether display type overrides should be enabled for the resulting object. If enabled, some C types
        will be displayed with an alternative text to make them easier to understand.
        For example, "struct data_processing_instruction" will be displayed as "Shifted Immediate".
        This feature is enabled by default.
        """
        self._enable_display_type_overrides = enable
        return self

    def _set_rw_array_symbol_index(self, rw_array_symbol_index: int) -> SymbolEntryBuilder:
        self._rw_array_symbol_index = rw_array_symbol_index
        return self

    def build(self) -> SymbolEntry:
        """
        Creates a new SymbolEntry with the data provided to the builder.
        The following mandatory fields must have been initialized before this method can be called: ROM project,
        C type, R/W Symbol, Binary ID, and Binary protocol.
        :raises ValueError If at least one of the required fields has not been initialized
        """
        if (
            self._rom_project is not None
            and self._c_type is not None
            and self._rw_symbol is not None
            and self._binary_id != ""
            and self._binary_protocol is not None
        ):
            value_type = self._get_value_column_type()

            return SymbolEntry(
                self._rom_project,
                self._name,
                self._c_type,
                self._description,
                self._rw_symbol,
                self._binary_id,
                self._binary_protocol,
                value_type,
                self._enable_display_type_overrides,
                self._get_children(),
            )
        else:
            raise ValueError("At least one required fields was not set")

    def _get_value_column_type(self) -> SymbolEntryValueType:
        """
        Returns the value column type that should be used for the entry represented by this builder, given the
        information contained in it so far.
        """
        if isinstance(self._rw_symbol, RWSimpleSymbol):
            # Try to get equivalent enum type, if it exists
            type_str = get_enum_equivalent_type(str(self._c_type))
            return SymbolEntryValueType.from_c_type(type_str)
        else:
            # Array and struct types don't have a visible value column
            return SymbolEntryValueType.EMPTY

    def _get_children(self) -> List[SymbolEntry]:
        """
        Creates all children for the current symbol entry. The resulting list will be empty if the entry is not
        an array or struct entry.
        The same mandatory fields listed in build() must have been initialized before this method can be called.
        :raises ValueError If at least one of the required fields has not been initialized
        """
        if (
            self._rom_project is not None
            and self._c_type is not None
            and self._rw_symbol is not None
            and self._binary_id != ""
            and self._binary_protocol is not None
        ):
            if isinstance(self._rw_symbol, RWSimpleSymbol):
                return []
            elif isinstance(self._rw_symbol, RWArraySymbol):
                result = []
                child_type = CType.dim_down_array_type(self._c_type)
                if len(self._c_type.dim_sizes) == 1:
                    # Simple array, create a simple entry for each element
                    for i in range(self._c_type.dim_sizes[0]):
                        new_child = (
                            SymbolEntryBuilder()
                            .set_rom_project(self._rom_project)
                            .set_name(self._name + "[" + str(i) + "]")
                            .set_c_type(child_type)
                            .set_description("")
                            .set_rw_data(
                                self._rw_symbol.elements[self._rw_array_symbol_index + i],
                                self._binary_id,
                                self._binary_protocol,
                            )
                            .build()
                        )
                        result.append(new_child)
                else:
                    # Multi-dimensional array, create an array entry for each element
                    for i in range(self._c_type.dim_sizes[0]):
                        child_rw_array_symbol_index = (
                            self._rw_array_symbol_index + child_type.get_total_num_elements() * i
                        )
                        new_child = (
                            SymbolEntryBuilder()
                            ._set_rw_array_symbol_index(child_rw_array_symbol_index)
                            .set_rom_project(self._rom_project)
                            .set_name(self._name + "[" + str(i) + "]")
                            .set_c_type(child_type)
                            .set_description("")
                            .set_rw_data(self._rw_symbol, self._binary_id, self._binary_protocol)
                            .build()
                        )
                        result.append(new_child)
                return result
            elif isinstance(self._rw_symbol, RWStructSymbol):
                result = []
                struct_fields = get_struct_fields(str(self._c_type))
                for field in struct_fields:
                    child_rw_symbol = self._rw_symbol.fields[field.name]
                    new_child = (
                        SymbolEntryBuilder()
                        .set_rom_project(self._rom_project)
                        .set_name(self._name + "." + field.name)
                        .set_c_type(CType.from_str(field.type))
                        .set_description("")
                        .set_rw_data(child_rw_symbol, self._binary_id, self._binary_protocol)
                        .build()
                    )
                    result.append(new_child)
                return result
            else:
                raise ValueError("Unknown RWSymbol subtype")
        else:
            raise ValueError("At least one required fields was not set")
