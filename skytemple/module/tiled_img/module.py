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
from gi.repository.Gtk import TreeStore

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.rom_project import RomProject


class TiledImgModule(AbstractModule):
    """Utility module that provides common dialogs for MapBGs and dungeon graphics."""
    @classmethod
    def depends_on(cls):
        return []

    @classmethod
    def sort_order(cls):
        return 0  # n/a

    def __init__(self, rom_project: RomProject):
        pass

    def load_tree_items(self, item_store: TreeStore, root_node):
        pass
