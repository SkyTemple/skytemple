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
import os
from typing import cast, Any

from gi.repository import Gtk

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.ui_utils import data_dir


class StStatusPageData:
    __slots__ = ['icon_name', 'title', 'description']
    icon_name: str
    title: str
    description: str

    def __init__(self, icon_name: str, title: str, description: str):
        self.icon_name = icon_name
        self.title = title
        self.description = description


@Gtk.Template(filename=os.path.join(data_dir(), 'widget', 'status_page.ui'))
class StStatusPage(Gtk.Box):
    """
    An base view widget that presents a single large icon and a description text.

    This will eventually be implemented using `Adw.StatusPage`, however until
    the GTK 4 migration is done, this is a custom widget.

    The `item_data` is an instance of `StStatusPageData`.
    """
    __gtype_name__ = "StStatusPage"

    module: AbstractModule
    item_data: StStatusPageData

    image_w = cast(Gtk.Image, Gtk.Template.Child())
    title_w = cast(Gtk.Label, Gtk.Template.Child())
    description_w = cast(Gtk.Label, Gtk.Template.Child())

    # noinspection PyUnusedLocal
    def __init__(self, module: AbstractModule, item_data: Any):
        super().__init__()

        assert isinstance(item_data, StStatusPageData)

        self.image_w.props.icon_name = item_data.icon_name
        self.title_w.props.label = item_data.title
        self.description_w.props.label = item_data.description
