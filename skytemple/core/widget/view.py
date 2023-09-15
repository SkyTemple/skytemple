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

from typing import Any, TYPE_CHECKING

from gi.repository import Gtk
from gi.repository import GObject


if TYPE_CHECKING:
    from skytemple.core.abstract_module import AbstractModule


class StView(Gtk.Box):
    """
    A view widget. This is a simple container for other widgets.
    It has two primary properties that are passed in when a view is loaded:

    - module: The `AbstractModule` that the view was loaded from.
    - item_data: The `item_data` (or `item_id` as it's sometimes referred to)
                 object that can provide additional context to the view, such
                 as a file name or ID that is currently being edited.

    To be inserted into the main item tree store, see `AbstractModule.load_tree_items`.

    Due to how views are loaded and displayed, you should place all potentially fallible
    initialization code inside your `__init__`, however if you need to, you can also use
    the `realize` signal to initialize.
    """
    __gtype_name__ = "StView"

    module: AbstractModule
    item_data: Any

    def __init__(self, module: AbstractModule, item_data: Any):
        super().__init__()
        self.module = module
        self.item_data = item_data

    @GObject.Property(type=object)
    def prop_module(self):
        return self.module

    @prop_module.setter  # type: ignore
    def prop_module(self, value: AbstractModule):
        self.module = value

    @GObject.Property(type=object)
    def prop_item_data(self):
        return self.item_data

    @prop_item_data.setter  # type: ignore
    def prop_item_data(self, value: Any):
        self.item_data = value
