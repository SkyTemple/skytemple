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
import sys
from typing import Union, List, Optional

from gi.repository import Gtk
from gi.repository.Gtk import TreeStore

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.error_handler import display_error
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.open_request import OpenRequest, REQUEST_TYPE_MAP_BG
from skytemple.core.rom_project import RomProject
from skytemple.core.ui_utils import recursive_up_item_store_mark_as_modified, \
    recursive_generate_item_store_row_label
from skytemple.module.map_bg.controller.bg import BgController
from skytemple.module.map_bg.controller.folder import FolderController
from skytemple.module.map_bg.controller.main import MainController, MAPBG_NAME
from skytemple.module.map_bg.script.add_created_with_logo import AddCreatedWithLogo
from skytemple_files.common.types.file_types import FileType
from skytemple_files.graphics.bg_list_dat.model import BgList
from skytemple_files.graphics.bma.model import Bma
from skytemple_files.graphics.bpa.model import Bpa
from skytemple_files.graphics.bpc.model import Bpc
from skytemple_files.graphics.bpl.model import Bpl
from skytemple_files.common.i18n_util import f, _

MAP_BG_PATH = 'MAP_BG/'
MAP_BG_LIST = MAP_BG_PATH + 'bg_list.dat'
logger = logging.getLogger(__name__)


class MapBgModule(AbstractModule):
    @classmethod
    def depends_on(cls):
        return ['tiled_img']

    @classmethod
    def sort_order(cls):
        return 120

    def __init__(self, rom_project: RomProject):
        """Loads the list of backgrounds for the ROM."""
        self.project = rom_project
        self.bgs: BgList = rom_project.open_file_in_rom(MAP_BG_LIST, FileType.BG_LIST_DAT)

        self._tree_model = None
        self._tree_level_iter = []

    def load_tree_items(self, item_store: TreeStore, root_node):
        root = item_store.append(root_node, [
            'skytemple-e-mapbg-symbolic', MAPBG_NAME, self, MainController, 0, False, '', True
        ])
        sub_nodes = {
            'S': item_store.append(root, [
                'skytemple-folder-symbolic', _('S - System'), self, FolderController, 'S - System', False, '', True
            ]),
            'T': item_store.append(root, [
                'skytemple-folder-symbolic', _('T - Town'), self, FolderController, 'T - Town', False, '', True
            ]),
            'D': item_store.append(root, [
                'skytemple-folder-symbolic', _('D - Dungeon'), self, FolderController, 'D - Dungeon', False, '', True
            ]),
            'G': item_store.append(root, [
                'skytemple-folder-symbolic', _('G - Guild'), self, FolderController, 'G - Guild', False, '', True
            ]),
            'H': item_store.append(root, [
                'skytemple-folder-symbolic', _('H - Habitat'), self, FolderController, 'H - Habitat', False, '', True
            ]),
            'P': item_store.append(root, [
                'skytemple-folder-symbolic', _('P - Places'), self, FolderController, 'P - Places', False, '', True
            ]),
            'V': item_store.append(root, [
                'skytemple-folder-symbolic', _('V - Visual'), self, FolderController, 'V - Visual', False, '', True
            ]),
            'W': item_store.append(root, [
                'skytemple-folder-symbolic', _('W - Weather'), self, FolderController, 'W - Weather', False, '', True
            ])
        }
        # Other
        other = item_store.append(root, [
            'skytemple-folder-symbolic', _('Others'), self, FolderController, None, False, '', True
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
                    'skytemple-e-mapbg-symbolic', level.bma_name, self,  BgController, i, False, '', True
                ])
            )

        recursive_generate_item_store_row_label(self._tree_model[root])

    def handle_request(self, request: OpenRequest) -> Optional[Gtk.TreeIter]:
        if request.type == REQUEST_TYPE_MAP_BG:
            if request.identifier > len(self._tree_level_iter) - 1:
                return None
            return self._tree_level_iter[request.identifier]
        return None

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
            display_error(
                sys.exc_info(),
                str(err),
                _("Error adding the logo.")
            )
        else:
            md = SkyTempleMessageDialog(None,
                                        Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                        Gtk.ButtonsType.OK, _("Logo added successfully. Thank you!"), is_success=True)
            md.set_position(Gtk.WindowPosition.CENTER)
            md.run()
            md.destroy()

    def get_associated_script_map(self, item_id):
        """Returns the script map that is associated to this map bg item ID, or None if not found"""
        for level in self.project.get_rom_module().get_static_data().script_data.level_list__by_id.values():
            if level.mapid == item_id:
                return level
        return None

    def remove_bpa_upper_layer(self, item_id):
        """
        A BPC layer was removed, change the BPAs for the entry item_id in the level list.
        Replace 0-4 with 5-8 and set 5-8 to None.
        """
        l = self.bgs.level[item_id]
        l.bpa_names = l.bpa_names[4:8] + [None, None, None, None]
        self.mark_level_list_as_modified()
