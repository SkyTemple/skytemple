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

from abc import ABC, abstractmethod
from typing import Optional, List

import pkg_resources
from gi.repository import Gtk
from gi.repository.Gtk import TreeStore, TreeIter

from skytemple.core.open_request import OpenRequest


class AbstractModule(ABC):
    """
    A SkyTemple module. First parameter of __init__ is RomProject.
    """
    @classmethod
    def load(cls):
        """
        An optional module init function. Called when the module itself is first loaded
        on UI load.
        """

    @classmethod
    @abstractmethod
    def depends_on(cls) -> List[str]:
        """
        A list of modules (names of entry_points), that this module depends on.
        """

    @classmethod
    @abstractmethod
    def sort_order(cls) -> int:
        """
        Where to sort this module in the item tree, lower numbers mean higher.
        """

    @abstractmethod
    def load_tree_items(self, item_store: TreeStore, root_node: Optional[TreeIter]):
        """Add the module nodes to the item tree"""
        pass

    def handle_request(self, request: OpenRequest) -> Optional[Gtk.TreeIter]:
        """
        Handle an OpenRequest. Must return the iterator for the view in the main view list, as generated
        in load_tree_items.
        If not implemented, always returns None
        """
        return None
