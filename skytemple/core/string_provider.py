#  Copyright 2020-2021 Parakoopa and the SkyTemple Contributors
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
import locale
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional, Union, List

from skytemple_files.common.ppmdu_config.data import Pmd2Language, Pmd2StringBlock
from skytemple_files.common.types.file_types import FileType
from skytemple_files.data.str.model import Str

if TYPE_CHECKING:
    from skytemple.core.rom_project import RomProject


class StringType(Enum):
    """This enum maps to entries from the Pmd2StringBlock of the Pmd2Data's Pmd2StringIndexData."""
    ITEM_NAMES = auto(), 'Item Names'
    MOVE_NAMES = auto(), 'Move Names'
    POKEMON_NAMES = auto(), 'Pokemon Names'
    POKEMON_CATEGORIES = auto(), 'Pokemon Categories'
    MOVE_DESCRIPTIONS = auto(), 'Move Descriptions'
    ITEM_LONG_DESCRIPTIONS = auto(), 'Item Long Descriptions'
    ITEM_SHORT_DESCRIPTIONS = auto(), 'Item Short Descriptions'
    TYPE_NAMES = auto(), 'Type Names'
    ABILITY_NAMES = auto(), 'Ability Names'
    ABILITY_DESCRIPTIONS = auto(), 'Ability Descriptions'
    PORTRAIT_NAMES = auto(), 'Portrait Names'
    GROUND_MAP_NAMES = auto(), 'Ground Map Names'
    DUNGEON_NAMES_MAIN = auto(), 'Dungeon Names (Main)'
    DUNGEON_NAMES_SELECTION = auto(), 'Dungeon Names (Selection)'
    DUNGEON_NAMES_SET_DUNGEON_BANNER = auto(), 'Dungeon Names (SetDungeonBanner)'
    DUNGEON_NAMES_BANNER = auto(), 'Dungeon Names (Banner)'
    DEFAULT_TEAM_NAMES = auto(), 'Default Team Names'
    RANK_NAMES = auto(), 'Explorer Ranks Names'
    DIALOGUE_LEVEL_UP = auto(), 'Pokemon LEVEL_UP Dialogue'
    DIALOGUE_WAIT = auto(), 'Pokemon WAIT Dialogue'
    DIALOGUE_HEALTHY = auto(), 'Pokemon HEALTHY Dialogue'
    DIALOGUE_HALF_LIFE = auto(), 'Pokemon HALF_LIFE Dialogue'
    DIALOGUE_PINCH = auto(), 'Pokemon PINCH Dialogue'
    DIALOGUE_GROUND_WAIT = auto(), 'Pokemon GROUND_WAIT Dialogue'
    WEATHER_NAMES = auto(), 'Weather Names'

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    # ignore the first param since it's already set by __new__
    def __init__(self, _: str, xml_name: str = None):
        self._xml_name_ = xml_name

    def __str__(self):
        return self._xml_name_

    def __repr__(self):
        return f'StringType.{self.name}'

    @property
    def xml_name(self):
        return self._xml_name_


LanguageLike = Union[str, Pmd2Language]  # locale string or Pmd2Language
MESSAGE_DIR = 'MESSAGE'


class StringProvider:
    """
    SpriteProvider. Provides strings from the big string table(s).
    """
    def __init__(self, project: 'RomProject'):
        self.project = project

    @property
    def _static_data(self):
        return self.project.get_rom_module().get_static_data()

    def get_value(self, string_type: StringType, index: int, language: LanguageLike = None) -> str:
        """
        Returns the value of a string in the big string file for the given language, starting from the offset
        defined by the string_type.
        If language is not set, the default ROM language is used.
        """
        model = self.get_model(language)
        return model.strings[self.get_index(string_type, index)]

    def get_index(self, string_type: StringType, index: int) -> int:
        """
        Returns the index of a string in the big string file for the given language, starting from the offset
        defined by the string_type.
        If language is not set, the default ROM language is used.
        """
        # TODO: We should probably also check the end offset (overflow check).
        return self._get_string_block(string_type).begin + index

    def get_all(self, string_type: StringType, language: LanguageLike = None) -> List[str]:
        """
        Returns all strings of the given type.
        If language is not set, the default ROM language is used.
        """
        model = self.get_model(language)
        string_block = self._get_string_block(string_type)
        return model.strings[string_block.begin:string_block.end]

    def get_model(self, language: LanguageLike = None) -> Str:
        """
        Returns the string table model for the given language.
        If language is not set, the default ROM language is used.
        """
        return self.project.open_file_in_rom(f'{MESSAGE_DIR}/{self._get_language(language).filename}', FileType.STR)

    def get_languages(self) -> List[Pmd2Language]:
        """Returns all supported languages."""
        return self._static_data.string_index_data.languages

    def mark_as_modified(self):
        for lang in self.get_languages():
            fname = f'{MESSAGE_DIR}/{lang.filename}'
            if self.project.is_opened(fname):
                self.project.mark_as_modified(fname)

    def _get_language(self, language_locale: LanguageLike = None) -> Pmd2Language:
        if isinstance(language_locale, Pmd2Language):
            return language_locale

        string_index_data = self._static_data.string_index_data
        language: Optional[Pmd2Language] = None
        if language_locale is None and len(string_index_data.languages) > 0:
            language = self._get_locale_from_app_locale()
        else:
            for lang in self.get_languages():
                if lang.locale == language_locale or lang.name == language_locale:
                    language = lang

        if language is None:
            raise ValueError(f"Language '{language_locale}' not found in ROM.")
        return language

    def _get_string_block(self, string_type: StringType) -> Pmd2StringBlock:
        string_index_data = self._static_data.string_index_data

        if string_type.xml_name not in string_index_data.string_blocks:
            raise ValueError(f"String mapping for {string_type} not found.")

        return string_index_data.string_blocks[string_type.xml_name]

    def _get_locale_from_app_locale(self) -> LanguageLike:
        try:
            current_locale = locale.getlocale()[0].split('_')[0]
            for lang in self.get_languages():
                lang_locale = lang.locale.split('-')[0]
                if lang_locale == current_locale:
                    return lang
            return self.get_languages()[0]
        except:
            return self.get_languages()[0]
