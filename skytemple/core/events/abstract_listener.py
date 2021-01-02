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
from abc import ABC
from typing import List

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.module_controller import AbstractController
from skytemple.core.rom_project import RomProject


class AbstractListener(ABC):
    """
    An abstract event listener. Implement a method to listen to an UI event.
    Implementing any method is optional. You can also implement 'on' for a generic
    event listener. This method will receive all events first and can also handle custom
    events.
    """
    def on_main_window_focus(self):
        """Triggered when the main window (re)-gains focus."""

    def on_debugger_window_focus(self):
        """Triggered when the debugger window (re)-gains focus."""

    def on_focus_lost(self):
        """Triggered when all of the SkyTemple windows have lost focus."""

    def on_project_open(self, project: RomProject):
        """Triggered, when a new project is loaded"""

    def on_view_switch(self, module: AbstractModule, controller: AbstractController, breadcrumbs: List[str]):
        """
        Triggered, when a view in the main UI was fully and successfully loaded.
        :param module: Instance of the module, that the view belongs to.
        :param controller: Instance of the controller that handles the loaded view
        :param breadcrumbs: List of strings of the path in the main UI tree that lead up to this view (as displayed
                            in the titlebar). The most inner level is the first entry.
        """

    def on_debugger_script_open(self, script_name: str):
        """Triggered, when the debugger opened a new script."""

    def on(self, event_name: str, *args, **kwargs):
        """
        Triggered on all UI events.
        :param event_name: Name of the event triggered
        :param args: Positional arguments, depending on the event.
        :param kwargs:
        """
        event_handler = getattr(self, f"on_{event_name}", None)
        if event_handler and callable(event_handler):
            event_handler(*args, **kwargs)
