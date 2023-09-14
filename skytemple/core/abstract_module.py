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
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, List, TypedDict, Dict, TYPE_CHECKING, Any, Union

from gi.repository import Gtk
from gi.repository.Gtk import TreeStore, TreeIter

from skytemple.core.open_request import OpenRequest
from skytemple_files.common.util import Captured

from skytemple.core.widget.view import StView

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
        """
        Add the module nodes to the item tree.

        The item store expects the following structure for items:

        - 0: str: icon name
        - 1: str: Label shown in UI. Should be translatable.
        - 2: AbstractModule: This module instance.
        - 3: Type[StView] or Type[AbstractController]: The widget or controller to display. Use StView for new code!
        - 4: Any: item_data for the controller or widget. This is basically a parameter to pass to it.
        - 5: 0
        - 6: False
        - 7: ''
        - 8: True
        """
        pass

    def collect_debugging_info(self, open_view: Union[AbstractController, StView]) -> Optional[DebuggingInfo]:
        """
        Return debugging information for the currently opened controller or view widget (passed in).
        If this module can't provide this information for that controller, returns None.
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
