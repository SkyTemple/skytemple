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

from skytemple.module.symbols.symbol_entry.symbol_entry import SymbolEntry
from skytemple.module.symbols.symbol_entry.symbol_entry_value_type import SymbolEntryValueType
# noinspection PyProtectedMember
from skytemple_files.common.i18n_util import _

from pmdsky_debug_py.protocol import Symbol, SectionProtocol

from gi.repository import Gtk

from skytemple.controller.main import MainController
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.rom_project import RomProject
from skytemple_files.common.rw_value import DATA_PROCESSING_INSTRUCTION_TYPE
from skytemple_files.hardcoded.symbols.c_type import CType
from skytemple_files.hardcoded.symbols.manual.equivalent_types import get_enum_equivalent_type
from skytemple_files.hardcoded.symbols.rw_symbol import RWSimpleSymbol

SHIFTED_IMMEDIATE_DISPLAY_TYPE = "Shifted Immediate"


class SimpleSymbolEntry(SymbolEntry):
    """
    Class used to represent a single simple entry on the symbol list. It's responsible for setting the required values
    on the UI model when created, as well as updating the underlying data when a callback takes place.
    """

    # RWSimpleSymbol instance used to read/write the value of the associated symbol
    rw_symbol: RWSimpleSymbol

    def __init__(self, rom_project: RomProject, binary_protocol: SectionProtocol, unique_id: int,
            tree_store: Gtk.TreeStore, parent_iter: Optional[Gtk.TreeIter], rw_symbol: RWSimpleSymbol, name_str: str,
            c_type: CType, desc_str: str, binary_id: str):
        """
        Creates a new simple symbol entry
        :param rw_symbol RWSimpleSymbol instance for the provided symbol
        :param name_str String to display as the name of the symbol. If it matches
        RWValue.DATA_PROCESSING_INSTRUCTION_TYPE, it will be converted to SHIFTED_IMMEDIATE_DISPLAY_TYPE.
        :param c_type C type of this symbol
        :param desc_str String to display as the description of the symbol
        :param binary_id ID of the binary this symbol belongs to
        """
        super().__init__(rom_project, binary_protocol, unique_id, tree_store, parent_iter)
        self.rw_symbol = rw_symbol

        if c_type.base_type == DATA_PROCESSING_INSTRUCTION_TYPE:
            # Since we only edit the shifted immediate part of instructions, we use a different display type for these
            type_str = SHIFTED_IMMEDIATE_DISPLAY_TYPE
        else:
            type_str = str(c_type)

        binary = self.rom_project.get_binary(self.binary_protocol)
        value = self.rw_symbol.get_rw_value().read_str(binary)

        # Determine the type of value column to use
        # Try to get equivalent enum type, if it exists
        type_str = get_enum_equivalent_type(type_str)
        value_type = SymbolEntryValueType.from_c_type(type_str)

        self._append_to_tree_store(name_str, type_str, desc_str, value, unique_id, binary_id, value_type)

    @classmethod
    def from_symbol(cls, rom_project: RomProject, binary_protocol: SectionProtocol, unique_id: int,
            tree_store: Gtk.TreeStore, parent_iter: Optional[Gtk.TreeIter], rw_symbol: RWSimpleSymbol, symbol: Symbol,
            binary_id: str):
        """
        Creates a new simple symbol entry. The name, description and type to display will be pulled from the provided
        Symbol instance.
        :raises ValueError If the provided symbol has no type
        """
        if symbol.c_type is None:
            raise ValueError("Cannot create a symbol entry from a symbol with no type")
        else:
            return cls(rom_project, binary_protocol, unique_id, tree_store, parent_iter, rw_symbol, symbol.name,
                CType.from_str(symbol.c_type), symbol.description, binary_id)

    def set_value(self, value: str) -> bool:
        """
        Updates the underlying value of the entry on the corresponding binary. If the operaion raises an error,
        it is displayed to the user.
        :return True if the value was successfully changed, false otherwise
        """
        try:
            self.rom_project.modify_binary(self.binary_protocol, lambda binary:
                self.rw_symbol.get_rw_value().write_str(binary, value))
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
