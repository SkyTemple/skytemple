from gi.repository.Gtk import TreeStore

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.rom_project import RomProject
from skytemple.core.ui_utils import recursive_generate_item_store_row_label
from skytemple.module.portrait.controller.main import MainController
from skytemple.module.portrait.controller.portrait import PortraitController
from skytemple_files.common.types.file_types import FileType
from skytemple_files.graphics.kao.model import Kao

PORTRAIT_FILE = 'FONT/kaomado.kao'


class PortraitModule(AbstractModule):
    @classmethod
    def depends_on(cls):
        return []

    def __init__(self, rom_project: RomProject):
        """Loads the list of backgrounds for the ROM."""
        self.project = rom_project
        self.kao: Kao = self.project.open_file_in_rom(PORTRAIT_FILE, FileType.KAO)

        self._tree_model = None
        self._tree_level_iter = []

    def load_tree_items(self, item_store: TreeStore):
        # TODO: Add to rom root node
        root = item_store.append(None, [
            'system-users', 'Portraits', self, MainController, 0, False, ''
        ])
        self._tree_model = item_store
        self._tree_level_iter = []
        for i in range(0, self.kao.toc_len):
            self._tree_level_iter.append(
                # TODO: More info, names, gender etc.
                item_store.append(root, [
                    'user-info', f'{i:04}', self,  PortraitController, i, False, ''
                ])
            )

        recursive_generate_item_store_row_label(self._tree_model[root])
