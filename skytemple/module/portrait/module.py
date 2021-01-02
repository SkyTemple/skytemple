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
from gi.repository import Gtk
from gi.repository.Gtk import TreeStore

from skytemple.controller.main import MainController
from skytemple.core.abstract_module import AbstractModule
from skytemple.core.rom_project import RomProject
from skytemple.module.portrait.portrait_provider import PortraitProvider
from skytemple.module.portrait.controller.portrait import PortraitController
from skytemple_files.common.types.file_types import FileType
from skytemple_files.graphics.kao.model import Kao, KaoImage

PORTRAIT_FILE = 'FONT/kaomado.kao'


class PortraitModule(AbstractModule):
    """Provides editing and displaying functionality for portraits."""
    @classmethod
    def depends_on(cls):
        return []

    @classmethod
    def sort_order(cls):
        return 0  # n/a

    def __init__(self, rom_project: RomProject):
        """Loads the list of backgrounds for the ROM."""
        self.project = rom_project
        self.kao: Kao = self.project.open_file_in_rom(PORTRAIT_FILE, FileType.KAO)
        self._portrait_provider = PortraitProvider(self.kao)
        self._portrait_provider__was_init = False

    def load_tree_items(self, item_store: TreeStore, root_node):
        """This module does not have main views."""
        pass

    def get_editor(self, item_id: int, modified_callback) -> Gtk.Widget:
        """Returns the view for one portrait slots"""
        controller = PortraitController(self, item_id, modified_callback)
        return controller.get_view()

    def get_portrait_provider(self) -> PortraitProvider:
        if not self._portrait_provider__was_init:
            self._portrait_provider.init_loader(MainController.window().get_screen())
            self._portrait_provider__was_init = True
        return self._portrait_provider

    def mark_as_modified(self):
        self.project.mark_as_modified(PORTRAIT_FILE)
