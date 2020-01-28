"""Module to load a module view and controller"""
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

from typing import TYPE_CHECKING

from gi.repository.Gtk import Widget

from skytemple.core.module_controller import AbstractController
from skytemple.core.task import AsyncTaskRunner
from skytemple.core.ui_signals import SIGNAL_VIEW_LOADED_ERROR, SIGNAL_VIEW_LOADED

if TYPE_CHECKING:
    from skytemple.core.abstract_module import AbstractModule


async def load_controller(module: 'AbstractModule', controller_class, item_id: int, go=None):
    # TODO
    try:
        controller: AbstractController = controller_class(module, item_id)
        AsyncTaskRunner.emit(go, SIGNAL_VIEW_LOADED, module, controller, item_id)
    except Exception as err:
        if go:
            AsyncTaskRunner.emit(go, SIGNAL_VIEW_LOADED_ERROR, err)
