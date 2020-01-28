#  Copyright 2020 Parakoopa
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

import os
from abc import ABC, abstractmethod

from gi.repository import Gtk
from gi.repository.Gtk import Widget

from skytemple.core.abstract_module import AbstractModule


class AbstractController(ABC):
    @abstractmethod
    def __init__(self, module: AbstractModule, item_id: int):
        """NO Gtk operations allowed here, not threadsafe!"""
        pass

    @abstractmethod
    def get_view(self) -> Widget:
        pass

    @staticmethod
    def _get_builder(pymodule_path: str, glade_file: str):
        path = os.path.abspath(os.path.dirname(pymodule_path))
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(path, glade_file))
        return builder
