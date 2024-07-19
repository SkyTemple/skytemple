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
from enum import Enum, auto

from skytemple.module.symbols.model_getter import ModelGetter


# List of enum types that should be displayed using dropdowns
ENUM_TYPES_DROPDOWN = [
    "enum secondary_terrain_type",
    "enum type_id",
    "enum type_matchup",
    "enum nature_power_variant",
    "enum status_two_turn_id",
    "enum exclusive_item_effect_id",
]

# List of enum types that should be displayed using a text with completion box
ENUM_TYPES_COMPLETION = ["enum monster_id", "enum item_id", "enum move_id", "enum music_id", "enum dungeon_id"]


class SymbolEntryValueType(Enum):
    """
    Used to identify the different types of value cells that symbol UI entries can have
    """

    # No value is shown
    EMPTY = auto()
    # The value is displayed as an editable string
    TEXT = auto()
    # The value is displayed as an editable boolean switch
    BOOLEAN = auto()
    # The value is displayed as a dropdown
    DROPDOWN = auto()
    # The value is displayed as a text field with a list of autocomplete values
    COMPLETION = auto()

    @classmethod
    def from_c_type(cls, c_type: str) -> SymbolEntryValueType:
        """
        Given a C type, returns the type of value cell that should be used to represent it.
        For enum types, if the type is not supported by ModelGetter or it's not listed in ENUM_TYPES_DROPDOWN or
        ENUM_TYPES_COMPLETION, returns TEXT.
        Warning! This method does not perform any type checks or conversions. Array and struct types will return TEXT,
        as they aren't directly supported.
        """
        if c_type == "bool":
            return cls.BOOLEAN
        elif ModelGetter.get().is_type_supported(c_type):
            if c_type in ENUM_TYPES_DROPDOWN:
                return cls.DROPDOWN
            elif c_type in ENUM_TYPES_COMPLETION:
                return cls.COMPLETION
            else:
                return cls.TEXT
        else:
            return cls.TEXT
