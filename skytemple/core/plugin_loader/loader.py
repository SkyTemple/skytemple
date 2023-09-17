#  Copyright 2020-2023 Capypara and the SkyTemple Contributors
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
import os.path
from importlib.abc import SourceLoader
from typing import Union


class SkyTemplePluginLoader(SourceLoader):
    def __init__(self, path: str):
        self.__path = path

    def get_data(self, path: Union[str, bytes]) -> bytes:
        with open(path, 'rb') as f:
            return f.read()

    def get_filename(self, fullname: str) -> str:
        if os.path.isdir(self.__path):
            return os.path.join(self.__path, '__init__.py')
        return self.__path
