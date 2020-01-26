import os
from abc import ABC, abstractmethod

from gi.repository import Gtk
from gi.repository.Gtk import Widget

from skytemple.core.abstract_module import AbstractModule


class AbstractController(ABC):
    @abstractmethod
    def __init__(self, module: AbstractModule, item_id: int):
        """NO Gtk operations allowed here, not threadsafe!"""
        pass

    @abstractmethod
    def get_view(self) -> Widget:
        pass

    @staticmethod
    def _get_builder(pymodule_path: str, glade_file: str):
        path = os.path.abspath(os.path.dirname(pymodule_path))
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(path, glade_file))
        return builder
