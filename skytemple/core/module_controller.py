"""
:deprecated: The controller-based approach of presenting and controlling views has been
             replaced. See docs for `AbstractController`.
"""
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
import logging
import os
from abc import ABC, abstractmethod
from typing import Optional

from gi.repository import Gtk, Pango
from gi.repository.Gtk import Widget

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.ui_utils import make_builder

logger = logging.getLogger(__name__)


class AbstractController(ABC):
    """
    A view controller. Provides and controls widgets for the main UI.

    :deprecated: Use a `Gtk.Widget` instead.  See the `ItemTreeEntry.__init__` documentation for more info.
    """

    @abstractmethod
    def __init__(self, module: AbstractModule, item_id):
        """NO Gtk operations allowed here, not threadsafe!"""
        pass

    async def async_init(self):
        """
        Optional asynchronous initialization, called after __init__.
        NO Gtk operations allowed here, not threadsafe!
        """

    @abstractmethod
    def get_view(self) -> Widget:
        pass

    def unload(self):
        """
        Perform additional unloading tasks to make sure no dangling references of this controller exist after
        view switch.
        """
        # Delete all toplevel widgets introduced:
        builder: Optional[Gtk.Builder] = None
        if hasattr(self, "builder"):
            builder = getattr(self, "builder")
        if hasattr(self, "_builder"):
            builder = getattr(self, "_builder")
        if builder:
            for obj in builder.get_objects():
                # We are excluding Switches due to a PyGobject bug.
                if isinstance(obj, Gtk.Widget) and not isinstance(obj, Gtk.Switch):
                    obj.destroy()

    @staticmethod
    def _get_builder(pymodule_path: str, glade_file: str) -> Gtk.Builder:
        path = os.path.abspath(os.path.dirname(pymodule_path))
        return make_builder(os.path.join(path, glade_file))

    def __del__(self):
        logger.debug(f"{self.__class__.__name__} controller unloaded.")
