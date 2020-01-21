from gi.repository.Gtk import TreeStore

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.rom_project import RomProject


class TiledBgModule(AbstractModule):
    @classmethod
    def depends_on(cls):
        return []

    def __init__(self, rom_project: RomProject):
        pass

    def load_tree_items(self, item_store: TreeStore):
        # Nothing to add.
        pass
