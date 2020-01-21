from abc import ABC, abstractmethod

import pkg_resources
from gi.repository.Gtk import TreeStore

SKYTEMPLE_VERSION = pkg_resources.get_distribution("skytemple").version


class AbstractModule(ABC):
    """
    A SkyTemple module. First parameter of __init__ is RomProject.
    """
    @classmethod
    @abstractmethod
    def depends_on(cls):
        """
        A list of modules (names of entry_points), that this module depends on.
        """

    @classmethod
    def version(cls):
        """
        Version of the module. Returns SkyTemple version by default. Third party
        modules MUST override this.
        """
        return SKYTEMPLE_VERSION

    @abstractmethod
    def load_tree_items(self, item_store: TreeStore):
        """Add the module nodes to the item tree"""
        pass
