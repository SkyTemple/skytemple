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
from skytemple.core.abstract_module import AbstractModule
from skytemple.core.item_tree import (
    ItemTree,
    ItemTreeEntry,
)
from skytemple.core.rom_project import RomProject
from skytemple_files.common.i18n_util import _

from skytemple.module.music.widget.main import StMusicMainPage


class MusicModule(AbstractModule):
    @classmethod
    def depends_on(cls):
        return []

    @classmethod
    def sort_order(cls):
        return 900

    def __init__(self, rom_project: RomProject):
        self.project = rom_project

    def load_tree_items(self, item_tree: ItemTree):
        item_tree.add_entry(
            None,
            ItemTreeEntry(
                icon="skytemple-e-music-symbolic",
                name=_("Music"),
                module=self,
                view_class=StMusicMainPage,
                item_data=None,
            ),
        )
