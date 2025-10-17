#  Copyright 2020-2025 SkyTemple Contributors
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
from skytemple_files.common.i18n_util import _

from skytemple.core.abstract_module import AbstractModule, DebuggingInfo
from skytemple.core.item_tree import (
    ItemTree,
    ItemTreeEntry,
    ItemTreeEntryRef,
    RecursionType,
)
from skytemple.core.module_controller import AbstractController
from skytemple.core.rom_project import RomProject
from skytemple.core.widget.status_page import StStatusPageData, StStatusPage
from skytemple_files.common.types.file_types import FileType

from skytemple.module.bgp.widget.bgp import StBgpBgpPage

BGP_FILE_EXT = "bgp"


MAIN_VIEW_DATA = StStatusPageData(
    icon_name="skytemple-illust-background",
    title=_("Backgrounds"),
    description=_("This section lets you edit static backgrounds used in various places of the game."),
)


class BgpModule(AbstractModule):
    @classmethod
    def depends_on(cls):
        return []

    @classmethod
    def sort_order(cls):
        return 150

    def __init__(self, rom_project: RomProject):
        """Loads the list of backgrounds for the ROM."""
        self.project = rom_project
        self.list_of_bgps = self.project.get_files_with_ext(BGP_FILE_EXT)

        self._item_tree: ItemTree
        self._tree_level_iter: list[ItemTreeEntryRef] = []

    def load_tree_items(self, item_tree: ItemTree):
        root = item_tree.add_entry(
            None,
            ItemTreeEntry(
                icon="skytemple-e-bgp-symbolic",
                name=MAIN_VIEW_DATA.title,
                module=self,
                view_class=StStatusPage,
                item_data=MAIN_VIEW_DATA,
            ),
        )
        self._item_tree = item_tree
        self._tree_level_iter = []
        for i, bgp_name in enumerate(self.list_of_bgps):
            self._tree_level_iter.append(
                item_tree.add_entry(
                    root,
                    ItemTreeEntry(
                        icon="skytemple-e-bgp-symbolic",
                        name=bgp_name,
                        module=self,
                        view_class=StBgpBgpPage,
                        item_data=i,
                    ),
                )
            )

    def mark_as_modified(self, item_id):
        """Mark a specific bg as modified"""
        bgp_filename = self.list_of_bgps[item_id]
        self.project.mark_as_modified(bgp_filename)
        # Mark as modified in tree
        self._item_tree.mark_as_modified(self._tree_level_iter[item_id], RecursionType.UP)

    def get_bgp(self, item_id):
        bgp_filename = self.list_of_bgps[item_id]
        return self.project.open_file_in_rom(bgp_filename, FileType.BGP)

    def collect_debugging_info(self, open_view: AbstractController | Gtk.Widget) -> DebuggingInfo | None:
        if isinstance(open_view, StBgpBgpPage):
            return {"models": {self.list_of_bgps[open_view.item_data]: open_view.bgp}}
        return None
