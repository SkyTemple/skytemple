from gi.repository.Gtk import TreeStore

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.rom_project import RomProject
from skytemple.module.map_bg.controller.bg import BgController
from skytemple.module.map_bg.controller.folder import FolderController
from skytemple.module.map_bg.controller.main import MainController
from skytemple_files.common.types.file_types import FileType
from skytemple_files.graphics.bg_list_dat.model import BgList

MAP_BG_PATH = 'MAP_BG/bg_list.dat'


class MapBgModule(AbstractModule):
    @classmethod
    def depends_on(cls):
        return ['tiled_bg']

    def __init__(self, rom_project: RomProject):
        """Loads the list of backgrounds for the ROM."""
        self.bgs: BgList = rom_project.open_file_in_rom(MAP_BG_PATH, FileType.BG_LIST_DAT)

    def load_tree_items(self, item_store: TreeStore):
        # TODO: Add to rom root node
        # TODO Icon
        root = item_store.append(None, [
            'folder-pictures', 'Map Backgrounds', self, MainController, 0
        ])
        sub_nodes = {
            'S': item_store.append(root, [
                'folder', 'S - Special', self, FolderController, 0
            ]),
            'T': item_store.append(root, [
                'folder', 'T - Town / Test', self, FolderController, 0
            ]),
            'D': item_store.append(root, [
                'folder', 'D - Dungeon', self, FolderController, 0
            ]),
            'G': item_store.append(root, [
                'folder', 'G - Guild', self, FolderController, 0
            ]),
            'H': item_store.append(root, [
                'folder', 'H - ???', self, FolderController, 0
            ]),
            'P': item_store.append(root, [
                'folder', 'P - ???', self, FolderController, 0
            ]),
            'V': item_store.append(root, [
                'folder', 'V - Visual', self, FolderController, 0
            ]),
            'W': item_store.append(root, [
                'folder', 'W - ???', self, FolderController, 0
            ])
        }
        # Other
        other = item_store.append(root, [
            'folder', 'Other', self, FolderController, 0
        ])
        for i, level in enumerate(self.bgs.level):
            parent = other
            if level.bma_name[0] in sub_nodes.keys():
                parent = sub_nodes[level.bma_name[0]]
            item_store.append(parent, [
                # TODO: Name from Strings
                'image', level.bma_name, self,  BgController, i
            ])

