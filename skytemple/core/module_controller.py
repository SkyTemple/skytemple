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
import logging
import os
from abc import ABC, abstractmethod
from typing import Optional

from gi.repository import Gtk, Pango
from gi.repository.Gtk import Widget

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.ui_utils import APP, make_builder
logger = logging.getLogger(__name__)


class AbstractController(ABC):
    @abstractmethod
    def __init__(self, module: AbstractModule, item_id: any):
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
        if hasattr(self, 'builder'):
            builder = getattr(self, 'builder')
        if hasattr(self, '_builder'):
            builder = getattr(self, '_builder')
        if builder:
            for obj in builder.get_objects():
                # We are excluding Switches due to a PyGobject bug.
                if isinstance(obj, Gtk.Widget) and not isinstance(obj, Gtk.Switch):
                    obj.destroy()

    @staticmethod
    def _get_builder(pymodule_path: str, glade_file: str):
        path = os.path.abspath(os.path.dirname(pymodule_path))
        return make_builder(os.path.join(path, glade_file))

    def __del__(self):
        logger.debug(f'{self.__class__.__name__} controller unloaded.')


class NotImplementedController(AbstractController):
    def __init__(self, module: AbstractModule, item_id: int):
        pass

    def get_view(self) -> Widget:
        return Gtk.Label.new("(This view is not implemented)")


class SimpleController(AbstractController, ABC):
    def get_view(self) -> Widget:
        main_box: Gtk.Box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
        align: Gtk.Alignment = Gtk.Alignment.new(0.5, 0.5, 0.8, 0.8)
        main_box.pack_start(align, True, True, 0)
        content_box: Gtk.Box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
        align.add(content_box)

        icon_name = self.get_icon()
        if icon_name:
            icon: Gtk.Image = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.LARGE_TOOLBAR)
            icon.set_pixel_size(127)
        title_label: Gtk.Label = Gtk.Label.new(self.get_title())
        content: Gtk.Widget = self.get_content()
        title_label.get_style_context().add_class('skytemple-view-main-label')
        if icon_name:
            icon.set_margin_top(20)
            title_label.set_margin_top(20)
        else:
            title_label.set_margin_top(64)
        content.set_margin_top(40)
        if icon_name:
            content_box.pack_start(icon, False, True, 0)
        content_box.pack_start(title_label, False, True, 0)
        content_box.pack_start(content, False, True, 0)
        back_illust = self.get_back_illust()
        if back_illust:
            style: Gtk.StyleContext = main_box.get_style_context()
            style.add_class('back_illust')
            style.add_class(back_illust)
            style: Gtk.StyleContext = content_box.get_style_context()
            style.add_class('no_bg')

        main_box.show_all()
        return main_box

    @abstractmethod
    def get_title(self) -> str:
        pass

    @abstractmethod
    def get_content(self) -> Widget:
        pass

    @abstractmethod
    def get_icon(self) -> Optional[str]:
        pass

    def get_back_illust(self) -> Optional[str]:
        return None

    def generate_content_label(self, text: str) -> Gtk.Label:
        label = Gtk.Label(text)
        label.set_justify(Gtk.Justification.CENTER)
        label.set_line_wrap_mode(Pango.WrapMode.WORD)
        label.set_line_wrap(True)
        return label
