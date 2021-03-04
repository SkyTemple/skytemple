"""Manages the integration of SkyTemple Script Debugger (skytemple-ssb-debugger)."""
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
import os
from typing import Optional

from gi.repository import Gtk

from skytemple.core.rom_project import RomProject
from skytemple.core.ssb_debugger.context import SkyTempleMainDebuggerControlContext
from skytemple.core.ui_utils import APP, make_builder
from skytemple_ssb_debugger.controller.main import MainController as DebuggerMainController
from skytemple_ssb_debugger.emulator_thread import EmulatorThread
from skytemple_ssb_debugger.main import get_debugger_builder, get_debugger_package_dir


class DebuggerManager:
    def __init__(self):
        self._context: Optional[SkyTempleMainDebuggerControlContext] = None
        self._opened_main_window: Optional[Gtk.Window] = None
        self._opened_main_controller: Optional[DebuggerMainController] = None
        self._was_opened_once = False
        self.main_window = None

    def open(self, main_window):
        """Open the debugger (if not already opened) and focus it's UI."""
        if not self.is_opened():
            self._was_opened_once = True
            self._context = SkyTempleMainDebuggerControlContext(self)

            builder = make_builder(os.path.join(get_debugger_package_dir(), "debugger.glade"))
            self._opened_main_window: Gtk.Window = builder.get_object("main_window")
            self._opened_main_window.set_role("SkyTemple Script Engine Debugger")
            self._opened_main_window.set_title("SkyTemple Script Engine Debugger")

            self._opened_main_controller = DebuggerMainController(
                builder, self._opened_main_window, self._context
            )
            self.handle_project_change()
            self.main_window = main_window

        self._opened_main_window.present()

    def close(self):
        """
        Close the debugger and focus it's UI (to bring dialog boxes of it into foreground).
        Returns False if the debugger was not closed.
        """
        if not self.is_opened():
            return True
        return not self._opened_main_controller.on_main_window_delete_event()

    def check_save(self):
        """Checks if unsaved files exist, if so asks the user to save them."""
        if not self.is_opened():
            return True
        return self._opened_main_controller.editor_notebook.close_all_tabs()

    def destroy(self):
        """Free resources."""
        if self._was_opened_once:
            emu_instance = EmulatorThread.instance()
            if emu_instance is not None:
                emu_instance.end()
            EmulatorThread.destroy_lib()

    def is_opened(self):
        """Returns whether or not the debugger is opened."""
        should_be_opened = self._context is not None
        if should_be_opened:
            if self._opened_main_window not in Gtk.Window.list_toplevels():
                self.on_close()
                return False
        return should_be_opened

    def handle_project_change(self):
        """
        If the debugger is currently open, handles changing the project for it.
        The global singleton instance of RomProject is used.
        """
        project = RomProject.get_current()
        if project is not None and self.is_opened():
            self._opened_main_controller.load_rom()

    def open_ssb(self, ssb_filename, main_window):
        """Open a SSB file in the debugger and focus it."""
        self.open(main_window)
        self._opened_main_controller.editor_notebook.open_ssb(ssb_filename)

    def get_context(self) -> Optional[SkyTempleMainDebuggerControlContext]:
        """Returns the managing context for the debugger. Returns None if the debugger is not opened!"""
        return self._context

    def on_script_added(self, ssb_path, mapname, scene_type, scene_name):
        """Inform the debugger about a newly created SSB file."""
        if self.is_opened():
            self._opened_main_controller.on_script_added(ssb_path, mapname, scene_type, scene_name)

    def on_script_removed(self, ssb_path):
        """Inform the debugger about a removed SSB file."""
        if self.is_opened():
            self._opened_main_controller.on_script_removed(ssb_path)

    # CONTEXT PRIVATE:

    def on_close(self):
        """(Internal, only to be called by the Context). Mark as closed."""
        self._context = None
        self._opened_main_window = None
        self._opened_main_controller = None

    def get_controller(self) -> Optional[DebuggerMainController]:
        return self._opened_main_controller

    def get_window(self) -> Optional[Gtk.Window]:
        return self._opened_main_window

