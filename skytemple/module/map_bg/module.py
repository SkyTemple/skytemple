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
import logging
from typing import Union, List

from gi.repository import Gtk
from gi.repository.Gtk import TreeStore

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.rom_project import RomProject
from skytemple.core.ui_utils import recursive_up_item_store_mark_as_modified, \
    recursive_generate_item_store_row_label
from skytemple.module.map_bg.controller.bg import BgController
from skytemple.module.map_bg.controller.folder import FolderController
from skytemple.module.map_bg.controller.main import MainController
from skytemple.module.map_bg.script.add_created_with_logo import AddCreatedWithLogo
from skytemple_files.common.types.file_types import FileType
from skytemple_files.graphics.bg_list_dat.model import BgList
from skytemple_files.graphics.bma.model import Bma
from skytemple_files.graphics.bpa.model import Bpa
from skytemple_files.graphics.bpc.model import Bpc
from skytemple_files.graphics.bpl.model import Bpl

MAP_BG_PATH = 'MAP_BG/'
MAP_BG_LIST = MAP_BG_PATH + 'bg_list.dat'
logger = logging.getLogger(__name__)


class MapBgModule(AbstractModule):
    @classmethod
    def depends_on(cls):
        return ['bgp']

    def __init__(self, rom_project: RomProject):
        """Loads the list of backgrounds for the ROM."""
        self.project = rom_project
        self.bgs: BgList = rom_project.open_file_in_rom(MAP_BG_LIST, FileType.BG_LIST_DAT)

        self._tree_model = None
        self._tree_level_iter = []

    def load_tree_items(self, item_store: TreeStore, root_node):
        root = item_store.append(root_node, [
            'folder-pictures', 'Map Backgrounds', self, MainController, 0, False, ''
        ])
        sub_nodes = {
            'S': item_store.append(root, [
                'folder', 'S - System', self, FolderController, 0, False, ''
            ]),
            'T': item_store.append(root, [
                'folder', 'T - Town', self, FolderController, 0, False, ''
            ]),
            'D': item_store.append(root, [
                'folder', 'D - Dungeon', self, FolderController, 0, False, ''
            ]),
            'G': item_store.append(root, [
                'folder', 'G - Guild', self, FolderController, 0, False, ''
            ]),
            'H': item_store.append(root, [
                'folder', 'H - Habitat', self, FolderController, 0, False, ''
            ]),
            'P': item_store.append(root, [
                'folder', 'P - Places', self, FolderController, 0, False, ''
            ]),
            'V': item_store.append(root, [
                'folder', 'V - Visual', self, FolderController, 0, False, ''
            ]),
            'W': item_store.append(root, [
                'folder', 'W - Weather', self, FolderController, 0, False, ''
            ])
        }
        # Other
        other = item_store.append(root, [
            'folder', 'Other', self, FolderController, 0, False, ''
        ])
        self._tree_model = item_store
        self._tree_level_iter = []
        for i, level in enumerate(self.bgs.level):
            parent = other
            if level.bma_name[0] in sub_nodes.keys():
                parent = sub_nodes[level.bma_name[0]]
            self._tree_level_iter.append(
                item_store.append(parent, [
                    # TODO: Name from Strings
                    'image', level.bma_name, self,  BgController, i, False, ''
                ])
            )

        recursive_generate_item_store_row_label(self._tree_model[root])

    def get_level_entry(self, item_id):
        return self.bgs.level[item_id]

    def get_bma(self, item_id) -> Bma:
        l = self.bgs.level[item_id]
        return self.project.open_file_in_rom(f'{MAP_BG_PATH}{l.bma_name.lower()}.bma', FileType.BMA)

    def get_bpc(self, item_id) -> Bpc:
        l = self.bgs.level[item_id]
        return self.project.open_file_in_rom(f'{MAP_BG_PATH}{l.bpc_name.lower()}.bpc', FileType.BPC)

    def get_bpl(self, item_id) -> Bpl:
        l = self.bgs.level[item_id]
        return self.project.open_file_in_rom(f'{MAP_BG_PATH}{l.bpl_name.lower()}.bpl', FileType.BPL)

    def get_bpas(self, item_id) -> List[Union[None, Bpa]]:
        l = self.bgs.level[item_id]
        bpas = []
        for bpa in l.bpa_names:
            if bpa is None:
                bpas.append(None)
            else:
                bpas.append(self.project.open_file_in_rom(f'{MAP_BG_PATH}{bpa.lower()}.bpa', FileType.BPA))
        return bpas

    def mark_as_modified(self, item_id):
        """Mark a specific map as modified"""
        l = self.bgs.level[item_id]
        self.project.mark_as_modified(f'{MAP_BG_PATH}{l.bma_name.lower()}.bma')
        self.project.mark_as_modified(f'{MAP_BG_PATH}{l.bpc_name.lower()}.bpc')
        self.project.mark_as_modified(f'{MAP_BG_PATH}{l.bpl_name.lower()}.bpl')
        self.project.mark_as_modified(f'{MAP_BG_PATH}{l.bma_name.lower()}.bma')
        for bpa in l.bpa_names:
            if bpa is not None:
                self.project.mark_as_modified(f'{MAP_BG_PATH}{bpa.lower()}.bpa')

        # Mark as modified in tree
        row = self._tree_model[self._tree_level_iter[item_id]]
        recursive_up_item_store_mark_as_modified(row)

    def mark_level_list_as_modified(self):
        self.project.mark_as_modified(MAP_BG_LIST)

    def add_created_with_logo(self):
        """Add a 'Created with SkyTemple' logo to S05P01A."""
        try:
            bma = self.project.open_file_in_rom(f'{MAP_BG_PATH}s05p01a.bma', FileType.BMA)
            bpc = self.project.open_file_in_rom(f'{MAP_BG_PATH}s05p01a.bpc', FileType.BPC)
            bpl = self.project.open_file_in_rom(f'{MAP_BG_PATH}s05p01a.bpl', FileType.BPL)

            AddCreatedWithLogo(bma, bpc, bpl).process()

            self.project.mark_as_modified(f'{MAP_BG_PATH}s05p01a.bma')
            self.project.mark_as_modified(f'{MAP_BG_PATH}s05p01a.bpc')
            self.project.mark_as_modified(f'{MAP_BG_PATH}s05p01a.bpl')
            item_id = -1
            for i, entry in enumerate(self.bgs.level):
                if entry.bma_name == 'S05P01A':
                    item_id = i
                    break
            if item_id != -1:
                row = self._tree_model[self._tree_level_iter[item_id]]
                recursive_up_item_store_mark_as_modified(row)
        except BaseException as err:
            logger.error("Logo add error", exc_info=err)
            md = Gtk.MessageDialog(None,
                                   Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                                   Gtk.ButtonsType.OK, str(err))
            md.set_position(Gtk.WindowPosition.CENTER)
            md.run()
            md.destroy()
        else:
            md = Gtk.MessageDialog(None,
                                   Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                   Gtk.ButtonsType.OK, "Logo added successfully. Thank you!")
            md.set_position(Gtk.WindowPosition.CENTER)
            md.run()
            md.destroy()
