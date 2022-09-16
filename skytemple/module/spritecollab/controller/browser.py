from gi.repository import Gtk, GLib

from skytemple.controller.main import MainController
from skytemple.core.abstract_module import AbstractModule
from skytemple.core.module_controller import AbstractController


class BrowserController(AbstractController):
    _instance = None

    def __init__(self, module: AbstractModule, _item_id):
        self.module = module
        self.builder: Gtk.Builder = None  # type: ignore
        self.was_realized = False

        self._store: Gtk.ListStore = None  # type: ignore
        self._filter: Gtk.TreeModelFilter = None  # type: ignore
        self._treev: Gtk.TreeView = None  # type: ignore
        self._search_text: str = ""

    @classmethod
    def get_instance(cls, module):
        if cls._instance is None:
            cls._instance = cls(module, None)
        return cls._instance

    def show(self):
        self.get_view().show()
        self.builder.connect_signals(self)
        # cool bug?
        self.builder.get_object('sc_left').set_hexpand(True)
        GLib.idle_add(lambda: self.builder.get_object('sc_left').set_hexpand(False))

    def get_view(self) -> Gtk.Window:
        self.builder = self._get_builder(__file__, 'browser.glade')
        window: Gtk.Window = self.builder.get_object('sc_window')
        window.set_transient_for(MainController.window())
        if not self.was_realized:
            window.resize(880, 530)

            self._store = Gtk.ListStore.new([bool, str, str])
            self._filter = self._store.filter_new()
            self._treev = self.builder.get_object('sc_tree')

            self._treev.set_model(self._filter)
            self._filter.set_visible_column(0)

            self.was_realized = True
        return window

    def on_sc_tree_selection_changed(self, selection: Gtk.TreeSelection):
        model, treeiter = selection.get_selected()
        if treeiter is not None and model is not None:
            raise NotImplementedError()

    def on_sc_settings_clicked(self, *args):
        raise NotImplementedError()

    def on_sc_external_clicked(self, *args):
        raise NotImplementedError()

    def on_sc_search_search_changed(self, search: Gtk.SearchEntry):
        """Filter the main item view using the search field"""
        self._search_text = search.get_text().strip()
        raise NotImplementedError()
