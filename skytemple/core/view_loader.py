"""Module to load a module view and controller"""
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

from typing import TYPE_CHECKING, Union, Any, Type

from gi.repository import Gtk
from gi.repository import GLib

from skytemple.core.module_controller import AbstractController

if TYPE_CHECKING:
    from skytemple.core.abstract_module import AbstractModule
    from skytemple.controller.main import MainController


async def load_view(
        module: 'AbstractModule',
        view: Union[Type[Gtk.Widget], Type[AbstractController]],
        item_data: Any,
        main_controller: MainController
):
    if issubclass(view, Gtk.Widget):
        try:
            # We use type: ignore here because there is an implicit contract that widgets used
            # for views must take these two arguments.
            view_instance = view(module=module, item_data=item_data)  # type: ignore
            GLib.idle_add(lambda: main_controller.on_view_loaded(module, view_instance, item_data))
        except Exception as ex:
            GLib.idle_add(lambda ex=ex: main_controller.on_view_loaded_error(ex))
    elif issubclass(view, AbstractController):
        # Legacy controller approach.
        try:
            controller: AbstractController = view(module, item_data)
            await controller.async_init()
            GLib.idle_add(lambda: main_controller.on_view_loaded(module, controller, item_data))
        except Exception as ex:
            GLib.idle_add(lambda ex=ex: main_controller.on_view_loaded_error(ex))
    else:
        raise ValueError("Invalid view object.")
