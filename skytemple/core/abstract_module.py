#  Copyright 2020-2021 Capypara and the SkyTemple Contributors
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
from typing import Optional, List, TypedDict, Dict, TYPE_CHECKING, Any

from gi.repository import Gtk
from gi.repository.Gtk import TreeStore, TreeIter

from skytemple.core.open_request import OpenRequest
from skytemple_files.common.util import Captured

if TYPE_CHECKING:
    from skytemple.core.module_controller import AbstractController


class DebuggingInfo(TypedDict, total=False):
    models: Dict[str, Any]
    additional: Optional[Captured]


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

    def collect_debugging_info(self, open_controller: 'AbstractController') -> Optional[DebuggingInfo]:
        """
        Return debugging information for the currently opened controller (passed in). If this module can't provide
        this information for that controller, returns None.
        If not implemented, always returns None.
        """
        return None

    def handle_request(self, request: OpenRequest) -> Optional[Gtk.TreeIter]:
        """
        Handle an OpenRequest. Must return the iterator for the view in the main view list, as generated
        in load_tree_items.
        If not implemented, always returns None.
        """
        return None
