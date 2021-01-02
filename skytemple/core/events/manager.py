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
import logging
from typing import List

from gi.repository import GLib

from skytemple.core.events.abstract_listener import AbstractListener
from skytemple.core.events.events import EVT_FOCUS_LOST, EVT_MAIN_WINDOW_FOCUS, EVT_DEBUGGER_WINDOW_FOCUS

logger = logging.getLogger(__name__)


class EventManager:
    """Class for handling UI events."""
    _instance = None

    def __init__(self):
        self._listeners: List[AbstractListener] = []

        self._a_window_had_focus = False
        self._main_window_focus = None
        self._debugger_window_focus = None
        self._will_check_focus = False

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def trigger(self, event_name: str, *args, **kwargs):
        """Triggers the specified UI event with the provided arguments."""
        logger.debug(f'Event {event_name} triggered.')
        for listener in self._listeners:
            try:
                listener.on(event_name, *args, **kwargs)
            except BaseException as ex:
                logger.error(
                    f'Error while handling event {event_name} with handler {listener}: {str(ex)}', exc_info=ex
                )

    def register_listener(self, listener_instance: AbstractListener):
        """Registers a listener to trigger events on."""
        if listener_instance not in self._listeners:
            self._listeners.append(listener_instance)

    def unregister_listener(self, listener_instance: AbstractListener):
        """Removes a previously registered listener"""
        if listener_instance in self._listeners:
            self._listeners.remove(listener_instance)

    def main_window_has_focus(self):
        if not self._main_window_focus:
            self._a_window_had_focus = True
            self._main_window_focus = True
            self.trigger(EVT_MAIN_WINDOW_FOCUS)

    def get_if_main_window_has_fous(self):
        return self._main_window_focus

    def main_window_lost_focus(self):
        self._main_window_focus = False
        if not self._will_check_focus:
            self._will_check_focus = True
            GLib.timeout_add_seconds(1, self.lost_foucs_check)

    def debugger_window_has_focus(self):
        if not self._debugger_window_focus:
            self._a_window_had_focus = True
            self._debugger_window_focus = True
            self.trigger(EVT_DEBUGGER_WINDOW_FOCUS)

    def debugger_window_lost_focus(self):
        self._debugger_window_focus = False
        if not self._will_check_focus:
            self._will_check_focus = True
            GLib.timeout_add_seconds(1, self.lost_foucs_check)

    def lost_foucs_check(self):
        """Check if both windows don't have focus."""
        self._will_check_focus = False
        if self._a_window_had_focus and not self._debugger_window_focus and not self._main_window_focus:
            self._a_window_had_focus = False
            self.trigger(EVT_FOCUS_LOST)
