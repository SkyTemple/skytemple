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

from abc import ABC, abstractmethod
from typing import Optional

import pkg_resources
from gi.repository.Gtk import TreeStore, TreeIter

SKYTEMPLE_VERSION = pkg_resources.get_distribution("skytemple").version


class AbstractModule(ABC):
    """
    A SkyTemple module. First parameter of __init__ is RomProject.
    """
    @classmethod
    @abstractmethod
    def depends_on(cls):
        """
        A list of modules (names of entry_points), that this module depends on.
        """

    @classmethod
    def version(cls):
        """
        Version of the module. Returns SkyTemple version by default. Third party
        modules MUST override this.
        """
        return SKYTEMPLE_VERSION

    @abstractmethod
    def load_tree_items(self, item_store: TreeStore, root_node: Optional[TreeIter]):
        """Add the module nodes to the item tree"""
        pass
