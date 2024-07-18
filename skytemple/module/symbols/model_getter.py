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
from typing import Dict, List

from skytemple_files.data.md.protocol import Gender

from skytemple_files.common.types.file_types import FileType

from skytemple.core.rom_project import RomProject

from gi.repository import Gtk

from skytemple.core.string_provider import StringType
from skytemple_files.hardcoded.symbols.manual.enums import get_enum_values, get_all_enum_types
from skytemple_files.hardcoded.symbols.unsupported_type_error import UnsupportedTypeError

# List of enum types that are handled dynamically. Their list of possible values is pulled from the ROM rather than
# from a fixed list of values.
DYNAMIC_ENUM_TYPES = ["enum monster_id", "enum item_id", "enum move_id", "enum music_id", "enum dungeon_id"]


class ModelGetter:
    """
    This class maps enum type names to the underlying models used by the UI to display the list of possible values.
    It can be used to retrieve the names of the models or the model instances.
    This class is a singleton. The class itself and its contained data will not be duplicated if multiple instances
    are requested.
    """

    _instance: ModelGetter | None = None

    project: RomProject
    # Dict that maps C types to their associated model instances
    models: Dict[str, Gtk.ListStore]

    def __new__(cls, rom_project: RomProject):
        if cls._instance is None:
            cls._instance = super(ModelGetter, cls).__new__(cls)
            cls._instance.project = rom_project
            cls._instance.models = {}
        return cls._instance

    @classmethod
    def get_or_create(cls, rom_project: RomProject) -> ModelGetter:
        """
        Gets the current instance of this class. If it has not been created yet, creates it first.
        """
        return cls(rom_project)

    @classmethod
    def get(cls) -> ModelGetter:
        """
        Returns the current instance of this class. If it has not been created yet, raises ValueError
        """
        if cls._instance is None:
            raise ValueError("Global instance not yet created. Call get_or_create() instead.")
        else:
            return cls._instance

    def is_type_supported(self, c_type: str) -> bool:
        """
        Given a C type, returns whether this class supports it (that is, if it's possible to create an UI element
        with a preset list of values of this type)
        """
        if c_type in DYNAMIC_ENUM_TYPES:
            return True
        else:
            try:
                get_enum_values(c_type)
                return True
            except (ValueError, UnsupportedTypeError):
                pass
        return False

    def get_all_supported_types(self) -> List[str]:
        """
        Returns a list with all the types supported by this class
        """
        return DYNAMIC_ENUM_TYPES + get_all_enum_types()

    def get_model(self, c_type: str) -> Gtk.ListStore:
        """
        Given a string representing a C enum type, returns the model instance associated to that type as a
        Gtk.ListStore. Each row in the ListStore will contain a possible value for the enum type. It will have two
        columns: one with the numeric ID of the value and another one with the string value.
        :param c_type C type
        :raises UnsupportedTypeError If the given C type is not supported
        :return Model instance associated to the given type
        """
        if self.is_type_supported(c_type):
            if c_type not in self.models:
                self.models[c_type] = self._create_model(c_type)
            return self.models[c_type]
        else:
            raise UnsupportedTypeError("The given type (" + c_type + ") is not supported")

    def _create_model(self, c_type: str) -> Gtk.ListStore:
        """
        Creates a new instance of a model given its associated type. It is assumed that the type is supported.
        """
        result = Gtk.ListStore(int, str)  # id, display string

        if c_type in DYNAMIC_ENUM_TYPES:
            # There has to be a better way of getting all the valid values of all these types than scraping existing
            # code for stuff to copy-paste
            if c_type == "enum monster_id":
                for i, entry in enumerate(self.project.get_module("monster").monster_md.entries):
                    name = self.project.get_string_provider().get_value(
                        StringType.POKEMON_NAMES, i % FileType.MD.properties().num_entities
                    )
                    result.append([i, f"{name} ({Gender(entry.gender).print_name}) (${i:04})"])  # type: ignore
            elif c_type == "enum item_id":
                for i, name in enumerate(self.project.get_string_provider().get_all(StringType.ITEM_NAMES)):
                    result.append([i, f"{name} (#{i:04})"])
            elif c_type == "enum move_id":
                for i, name in enumerate(self.project.get_string_provider().get_all(StringType.MOVE_NAMES)):
                    result.append([i, f"{name} (#{i:03})"])
            elif c_type == "enum music_id":
                for i, music_entry in self.project.get_rom_module().get_static_data().script_data.bgms__by_id.items():
                    result.append([i, f"{music_entry.name} (#{i:03})"])
            elif c_type == "enum dungeon_id":
                for i, name in enumerate(self.project.get_string_provider().get_all(StringType.DUNGEON_NAMES_MAIN)):
                    result.append([i, f"{name} (#{i:03})"])
            else:
                raise NotImplementedError()
        else:
            enum_values = get_enum_values(c_type)

            for enum_value in enum_values:
                result.append([enum_value.int_value, enum_value.name])

        return result
