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
import configparser
import logging
import os
from typing import Optional, Tuple, List

from skytemple_files.common.project_file_manager import ProjectFileManager
from skytemple_files.common.util import open_utf8

CONFIG_FILE_NAME = 'config.ini'

SECT_GENERAL = 'General'
SECT_WINDOW = 'Window'
SECT_RECENT_FILES = 'Recent'
SECT_INTEGRATION_DISCORD = 'Discord'

KEY_RECENT_1 = 'file1'
KEY_RECENT_2 = 'file2'
KEY_RECENT_3 = 'file3'
KEY_RECENT_4 = 'file4'
KEY_RECENT_5 = 'file5'

KEY_ASSISTANT_SHOWN = 'assistant_shown'
KEY_GTK_THEME = 'gtk_theme'
KEY_LOCALE = 'locale'

KEY_WINDOW_SIZE_X = 'width'
KEY_WINDOW_SIZE_Y = 'height'
KEY_WINDOW_POS_X = 'pos_x'
KEY_WINDOW_POS_Y = 'pos_y'

KEY_INTEGRATION_DISCORD_DISCORD_ENABLED = 'enabled'
logger = logging.getLogger(__name__)


class SkyTempleSettingsStore:
    def __init__(self):
        self.config_dir = os.path.join(ProjectFileManager.shared_config_dir())
        os.makedirs(self.config_dir, exist_ok=True)
        self.config_file = os.path.join(self.config_dir, CONFIG_FILE_NAME)
        self.loaded_config = configparser.ConfigParser()
        if os.path.exists(self.config_file):
            try:
                with open_utf8(self.config_file, 'r') as f:
                    self.loaded_config.read_file(f)
            except BaseException as err:
                logger.error("Error reading config, falling back to default.", exc_info=err)

    def get_recent_files(self) -> List[str]:
        recents = []
        if SECT_RECENT_FILES in self.loaded_config:
            if KEY_RECENT_1 in self.loaded_config[SECT_RECENT_FILES]:
                recents.append(self.loaded_config[SECT_RECENT_FILES][KEY_RECENT_1])
            if KEY_RECENT_2 in self.loaded_config[SECT_RECENT_FILES]:
                recents.append(self.loaded_config[SECT_RECENT_FILES][KEY_RECENT_2])
            if KEY_RECENT_3 in self.loaded_config[SECT_RECENT_FILES]:
                recents.append(self.loaded_config[SECT_RECENT_FILES][KEY_RECENT_3])
            if KEY_RECENT_4 in self.loaded_config[SECT_RECENT_FILES]:
                recents.append(self.loaded_config[SECT_RECENT_FILES][KEY_RECENT_4])
            if KEY_RECENT_5 in self.loaded_config[SECT_RECENT_FILES]:
                recents.append(self.loaded_config[SECT_RECENT_FILES][KEY_RECENT_5])
        return recents

    def set_recent_files(self, recent_files: List[str]):
        # We only save the last 5 opened files. If the list is smaller than the old list, old entries are kept.
        if SECT_RECENT_FILES not in self.loaded_config:
            self.loaded_config[SECT_RECENT_FILES] = {}
        if len(recent_files) > 0:
            self.loaded_config[SECT_RECENT_FILES][KEY_RECENT_1] = recent_files[0]
        if len(recent_files) > 1:
            self.loaded_config[SECT_RECENT_FILES][KEY_RECENT_2] = recent_files[1]
        if len(recent_files) > 2:
            self.loaded_config[SECT_RECENT_FILES][KEY_RECENT_3] = recent_files[2]
        if len(recent_files) > 3:
            self.loaded_config[SECT_RECENT_FILES][KEY_RECENT_4] = recent_files[3]
        if len(recent_files) > 4:
            self.loaded_config[SECT_RECENT_FILES][KEY_RECENT_5] = recent_files[4]
        self._save()

    def get_assistant_shown(self) -> bool:
        if SECT_GENERAL in self.loaded_config:
            if KEY_ASSISTANT_SHOWN in self.loaded_config[SECT_GENERAL]:
                return int(self.loaded_config[SECT_GENERAL][KEY_ASSISTANT_SHOWN]) > 0
        return False

    def set_assistant_shown(self, value: bool):
        if SECT_GENERAL not in self.loaded_config:
            self.loaded_config[SECT_GENERAL] = {}
        self.loaded_config[SECT_GENERAL][KEY_ASSISTANT_SHOWN] = '1' if value else '0'
        self._save()

    def get_gtk_theme(self, default=None) -> str:
        if SECT_GENERAL in self.loaded_config:
            if KEY_GTK_THEME in self.loaded_config[SECT_GENERAL]:
                return self.loaded_config[SECT_GENERAL][KEY_GTK_THEME]
        return default

    def set_gtk_theme(self, value: str):
        if SECT_GENERAL not in self.loaded_config:
            self.loaded_config[SECT_GENERAL] = {}
        self.loaded_config[SECT_GENERAL][KEY_GTK_THEME] = value
        self._save()

    def get_locale(self, default='') -> str:
        if SECT_GENERAL in self.loaded_config:
            if KEY_LOCALE in self.loaded_config[SECT_GENERAL]:
                return self.loaded_config[SECT_GENERAL][KEY_LOCALE]
        return default

    def set_locale(self, value: str):
        if SECT_GENERAL not in self.loaded_config:
            self.loaded_config[SECT_GENERAL] = {}
        self.loaded_config[SECT_GENERAL][KEY_LOCALE] = value
        self._save()

    def get_window_size(self) -> Optional[Tuple[int, int]]:
        if SECT_WINDOW in self.loaded_config:
            if KEY_WINDOW_SIZE_X in self.loaded_config[SECT_WINDOW] and KEY_WINDOW_SIZE_Y in self.loaded_config[SECT_WINDOW]:
                return int(self.loaded_config[SECT_WINDOW][KEY_WINDOW_SIZE_X]), int(self.loaded_config[SECT_WINDOW][KEY_WINDOW_SIZE_Y])
        return None

    def set_window_size(self, dim: Tuple[int, int]):
        if SECT_WINDOW not in self.loaded_config:
            self.loaded_config[SECT_WINDOW] = {}
        self.loaded_config[SECT_WINDOW][KEY_WINDOW_SIZE_X] = str(dim[0])
        self.loaded_config[SECT_WINDOW][KEY_WINDOW_SIZE_Y] = str(dim[1])
        self._save()

    def get_window_position(self) -> Optional[Tuple[int, int]]:
        if SECT_WINDOW in self.loaded_config:
            if KEY_WINDOW_POS_X in self.loaded_config[SECT_WINDOW] and KEY_WINDOW_POS_Y in self.loaded_config[SECT_WINDOW]:
                return int(self.loaded_config[SECT_WINDOW][KEY_WINDOW_POS_X]), int(self.loaded_config[SECT_WINDOW][KEY_WINDOW_POS_Y])
        return None

    def set_window_position(self, pos: Tuple[int, int]):
        if SECT_WINDOW not in self.loaded_config:
            self.loaded_config[SECT_WINDOW] = {}
        self.loaded_config[SECT_WINDOW][KEY_WINDOW_POS_X] = str(pos[0])
        self.loaded_config[SECT_WINDOW][KEY_WINDOW_POS_Y] = str(pos[1])
        self._save()

    def get_integration_discord_enabled(self) -> bool:
        if SECT_INTEGRATION_DISCORD in self.loaded_config:
            if KEY_INTEGRATION_DISCORD_DISCORD_ENABLED in self.loaded_config[SECT_INTEGRATION_DISCORD]:
                return int(self.loaded_config[SECT_INTEGRATION_DISCORD][KEY_INTEGRATION_DISCORD_DISCORD_ENABLED]) > 0
        return True  # default is enabled.

    def set_integration_discord_enabled(self, value: bool):
        if SECT_INTEGRATION_DISCORD not in self.loaded_config:
            self.loaded_config[SECT_INTEGRATION_DISCORD] = {}
        self.loaded_config[SECT_INTEGRATION_DISCORD][KEY_INTEGRATION_DISCORD_DISCORD_ENABLED] = '1' if value else '0'
        self._save()

    def _save(self):
        with open_utf8(self.config_file, 'w') as f:
            self.loaded_config.write(f)

