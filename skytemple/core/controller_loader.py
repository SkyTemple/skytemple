"""Module to load a module view and controller"""
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

from typing import TYPE_CHECKING

from gi.repository import GLib

from skytemple.core.module_controller import AbstractController

if TYPE_CHECKING:
    from skytemple.core.abstract_module import AbstractModule
    from skytemple.controller.main import MainController


async def load_controller(module: 'AbstractModule', controller_class, item_id: int, main_controller: 'MainController'):
    try:
        controller: AbstractController = controller_class(module, item_id)
        GLib.idle_add(lambda: main_controller.on_view_loaded(module, controller, item_id))
    except Exception as ex:
        GLib.idle_add(lambda ex=ex: main_controller.on_view_loaded_error(ex))
