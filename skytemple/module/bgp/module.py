from gi.repository.Gtk import TreeStore

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.rom_project import RomProject
from skytemple.core.ui_utils import recursive_generate_item_store_row_label
from skytemple.module.bgp.controller.bgp import BgpController
from skytemple.module.bgp.controller.main import MainController
BGP_FILE_EXT = 'bgp'


class BgpModule(AbstractModule):
    @classmethod
    def depends_on(cls):
        return []

    def __init__(self, rom_project: RomProject):
        """Loads the list of backgrounds for the ROM."""
        self.project = rom_project
        self.list_of_bgps = self.project.get_files_with_ext(BGP_FILE_EXT)

        self._tree_model = None
        self._tree_level_iter = []

    def load_tree_items(self, item_store: TreeStore):
        # TODO: Add to rom root node
        root = item_store.append(None, [
            'folder-pictures', 'Backgrounds', self, MainController, 0, False, ''
        ])
        self._tree_model = item_store
        self._tree_level_iter = []
        for i, bgp_name in enumerate(self.list_of_bgps):
            self._tree_level_iter.append(
                item_store.append(root, [
                    'image', bgp_name, self,  BgpController, i, False, ''
                ])
            )

        recursive_generate_item_store_row_label(self._tree_model[root])
