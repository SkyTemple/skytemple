import os
import traceback
from threading import current_thread

import gi

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.controller_loader import load_controller
from skytemple.core.module_controller import AbstractController
from skytemple.core.rom_project import RomProject, SIGNAL_OPENED
from skytemple.core.task import AsyncTaskRunner
from skytemple.core.ui_signals import SkyTempleSignalContainer, SIGNAL_OPENED_ERROR, SIGNAL_VIEW_LOADED, \
    SIGNAL_VIEW_LOADED_ERROR

gi.require_version('Gtk', '3.0')

from gi.repository import Gtk
from gi.repository.Gtk import *
from gi.repository.GObject import GObject
main_thread = current_thread()


class MainController:
    def __init__(self, builder: Builder, window: Window):
        self.builder = builder
        self.window = window

        # Created on demand
        self._loading_dialog: Dialog = None
        self._main_item_list: TreeView = None
        self._main_item_filter: TreeModel = None

        self._recent_files_store: ListStore = self.builder.get_object('recent_files_store')
        self._item_store: TreeStore = builder.get_object('item_store')
        self._editor_stack: Stack = builder.get_object('editor_stack')

        builder.connect_signals(self)
        window.connect("destroy", self.on_destroy)

        # Custom file-related signal container
        self._signal_container = SkyTempleSignalContainer()
        self._signal_container.connect(SIGNAL_OPENED, self.on_file_opened)
        self._signal_container.connect(SIGNAL_OPENED_ERROR, self.on_file_opened_error)
        self._signal_container.connect(SIGNAL_VIEW_LOADED, self.on_view_loaded)
        self._signal_container.connect(SIGNAL_VIEW_LOADED_ERROR, self.on_view_loaded_error)

        self._search_text = None
        self._current_view_module = None
        self._current_view_controller_class = None
        self._current_view_item_id = None

        self._load_position_and_size()
        self._configure_csd()
        self._load_icon()
        self._load_recent_files()
        self._connect_item_views()
        self._configure_error_view()

    def on_destroy(self, *args):
        AsyncTaskRunner.end()
        Gtk.main_quit()

    def on_open_more_clicked(self, button: Button):
        """Dialog to open a file"""
        dialog = Gtk.FileChooserDialog(
            "Open ROM...",
            self.window,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        )

        filter_nds = Gtk.FileFilter()
        filter_nds.set_name("Nintendo DS ROMs (*.nds)")
        filter_nds.add_mime_type("application/x-nintendo-ds-rom")
        filter_nds.add_pattern("*.nds")
        dialog.add_filter(filter_nds)

        filter_any = Gtk.FileFilter()
        filter_any.set_name("Any files")
        filter_any.add_pattern("*")
        dialog.add_filter(filter_any)

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.OK:
            self._open_file(fn)

    def on_open_tree_selection_changed(self, selection: TreeSelection):
        """Open a file selected in a tree"""
        model, treeiter = selection.get_selected()
        if treeiter is not None and model is not None:
            self._open_file(model[treeiter][0])

    def on_file_opened(self, c):
        """Update the UI after a ROM file has been opened."""
        assert current_thread() == main_thread

        self._init_window_after_rom_load(os.path.basename(RomProject.get_current().filename))

        # TODO: Load root node, ROM
        # Load item tree items
        try:
            for module in RomProject.get_current().modules():
                # TODO: Skip ROM module, add as child of ROM module
                module.load_tree_items(self._item_store)
                # TODO: Check multi language support in Strings module, enable language switcher
            # TODO: Load settings from ROM for history, bookmarks, etc? - separate module?

            # TODO: Select main ROM item by default
        except BaseException as ex:
            self.on_file_opened_error(c, ex)
            return

        if self._loading_dialog is not None:
            self._loading_dialog.hide()
            self._loading_dialog.destroy()
            self._loading_dialog = None

    def on_file_opened_error(self, c, exception):
        """Handle errors during file openings."""
        assert current_thread() == main_thread
        if self._loading_dialog is not None:
            self._loading_dialog.hide()
            self._loading_dialog.destroy()
            self._loading_dialog = None
        # TODO: Better exception display
        md = Gtk.MessageDialog(self.window,
                               Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                               Gtk.ButtonsType.OK, str(exception),
                               title="SkyTemple - Error!")
        md.set_position(Gtk.WindowPosition.CENTER)
        md.run()
        md.destroy()

    def on_main_item_list_selection_changed(self, selection: TreeSelection):
        """Handle click on item: Switch view"""
        model, treeiter = selection.get_selected()
        if model is not None and treeiter is not None and RomProject.get_current() is not None:
            selected_node = model[treeiter]
            self._init_window_before_view_load(model[treeiter])
            # Show loading stack page in editor stack
            self._editor_stack.set_visible_child(self.builder.get_object('es_loading'))
            # Set current view values for later check (if race conditions between fast switching)
            self._current_view_module = selected_node[2]
            self._current_view_controller_class = selected_node[3]
            self._current_view_item_id = selected_node[4]
            # Fully load the view and the controller
            AsyncTaskRunner.instance().run_task(load_controller(
                self._current_view_module, self._current_view_controller_class, self._current_view_item_id,
                self._signal_container
            ))

    def on_view_loaded(self, c, module: AbstractModule, controller: AbstractController, item_id: int):
        """A new module view was loaded! Present it!"""
        # Check if current view still matches expected
        if self._current_view_module != module or self._current_view_controller_class != controller.__class__ or self._current_view_item_id != item_id:
            return
        # TODO Insert the view at page 3 [0,1,2,3] of the stack. If there is already a page, remove it.
        pass

    def on_view_loaded_error(self, c, ex: BaseException):
        """An error during module view load happened :("""
        tb: TextBuffer = self.builder.get_object('es_error_text_buffer')
        tb.set_text(''.join(traceback.format_exception(etype=type(ex), value=ex, tb=ex.__traceback__)))
        self._editor_stack.set_visible_child(self.builder.get_object('es_error'))

    def on_main_item_list_search_search_changed(self, search: Gtk.SearchEntry):
        """Filter the main item view using the search field"""
        self._search_text = search.get_text()
        self._main_item_filter.refilter()

    def _load_position_and_size(self):
        # TODO
        self.window.set_position(Gtk.WindowPosition.CENTER)
        self.window.resize(900, 600)

    def _configure_csd(self):
        # TODO. Following code disables CSD.
        return
        tb: HeaderBar = self.window.get_titlebar()
        self.window.set_titlebar(None)
        main_box: Box = self.window.get_child()
        main_box.add(tb)
        main_box.reorder_child(tb, 0)
        tb.set_show_close_button(False)

    def _load_icon(self):
        if not self.window.get_icon():
            # Load default icon if not already defined (in the Glade file the name "skytemple" is set.
            # TODO
            self.window.set_icon_name('image-missing')
            #main_window.set_icon_from_file(get_resource_path("icon.png"))

    def _load_recent_files(self):
        # TODO. Also check if all recent files still exist!
        recent_file_list = []

        sw_header: ScrolledWindow = self.builder.get_object('open_tree_sw')
        sw_header.set_min_content_width(285)
        sw_header.set_min_content_height(130)
        sw_main: ScrolledWindow = self.builder.get_object('open_tree_main_sw')
        sw_main.set_min_content_width(285)
        sw_main.set_min_content_height(130)

        if len(recent_file_list) < 1:
            self.builder.get_object('recent_files_main_label').set_visible(False)
            self.builder.get_object('open_tree_main_sw').set_visible(False)
            self.builder.get_object('open_tree_sw').set_visible(False)
            self.builder.get_object('open_more').set_label("Open a ROM")
            self.builder.get_object('open_more_main').set_label("Open a ROM")
        else:
            for f in recent_file_list:
                dir_name = os.path.dirname(f)
                file_name = os.path.basename(f)
                self._recent_files_store.append([f, f"{file_name} ({dir_name})"])
            open_tree: TreeView = self.builder.get_object('open_tree')
            open_tree_main: TreeView = self.builder.get_object('open_tree_main')

            column = TreeViewColumn("Filename", Gtk.CellRendererText(), text=1)
            column_main = TreeViewColumn("Filename", Gtk.CellRendererText(), text=1)

            open_tree.append_column(column)
            open_tree_main.append_column(column_main)

            open_tree.set_model(self._recent_files_store)
            open_tree_main.set_model(self._recent_files_store)

    def _open_file(self, filename: str):
        """Open a file"""
        if self._check_open_file():
            self._loading_dialog = self.builder.get_object('file_opening_dialog')
            self.builder.get_object('file_opening_dialog_label').set_label(
                f'Loading ROM "{os.path.basename(filename)}"...'
            )
            RomProject.open(filename, self._signal_container)
            self._loading_dialog.run()

    def _check_open_file(self):
        """Check for open files, and ask the user what to do. Returns false if they cancel."""
        rom = RomProject.get_current()
        if rom is not None:
            dialog: MessageDialog = Gtk.MessageDialog(
                self.window,
                Gtk.DialogFlags.MODAL,
                Gtk.MessageType.WARNING,
                Gtk.ButtonsType.NONE, f"Do you want to save changes to {os.path.basename(rom.filename)}?"
            )
            dont_save: Widget = dialog.add_button("Don't Save", 0)
            dont_save.get_style_context().add_class('destructive-action')
            dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
            dialog.add_button("Save", 1)
            dialog.format_secondary_text(f"If you don't save, your changes will be lost.")
            response = dialog.run()
            dialog.destroy()

            if response == 0:
                # Don't save
                return True
            elif response == 1:
                # Save (True on success, False on failure. Don't close the file if we can't save it...)
                return self._save_file(rom)
            else:
                # Cancel
                return False
        return True

    def _connect_item_views(self):
        """Connect the all items, recent items and favorite items views"""
        main_item_list: TreeView = self.builder.get_object('main_item_list')

        icon = TreeViewColumn("Icon", Gtk.CellRendererPixbuf(), icon_name=0)
        column = TreeViewColumn("Title", Gtk.CellRendererText(), text=1)

        main_item_list.append_column(icon)
        main_item_list.append_column(column)

        self._main_item_filter = self._item_store.filter_new()
        self._main_item_list = main_item_list

        main_item_list.set_model(self._main_item_filter)
        self._main_item_filter.set_visible_func(self._main_item_filter_func)

        # TODO: Recent and Favorites

    def _main_item_filter_func(self, model, iter, data):
        return self._recursive_filter_func(self._search_text, model, iter)

    def _recursive_filter_func(self, search, model, iter):
        if search is None:
            return True
        i_match = search.lower() in model[iter][1].lower()
        if i_match:
            return True
        for child in model[iter].iterchildren():
            child_match = self._recursive_filter_func(search, child.model, child.iter)
            if child_match:
                self._main_item_list.expand_row(child.parent.path, False)
                return True
        return False

    def _configure_error_view(self):
        sw: ScrolledWindow = self.builder.get_object('es_error_text_sw')
        sw.set_min_content_width(200)
        sw.set_min_content_height(300)

    def _init_window_after_rom_load(self, rom_name):
        """Set the titlebar and make buttons sensitive after a ROM load"""
        self._item_store.clear()
        self.builder.get_object('save_button').set_sensitive(True)
        self.builder.get_object('save_as_button').set_sensitive(True)
        self.builder.get_object('main_item_list_search').set_sensitive(True)
        # TODO: Titlebar for Non-CSD situation
        tb: HeaderBar = self.window.get_titlebar()
        tb.set_title(f"{rom_name} (SkyTemple)")

    def _init_window_before_view_load(self, node: TreeModelRow):
        """Update the subtitle / breadcrumb before switching views"""
        bc = ""
        parent = node
        while parent:
            bc = f" > {parent[1]}" + bc
            parent = parent.parent
        bc = bc[3:]
        # TODO: Titlebar for Non-CSD situation
        self.window.get_titlebar().set_subtitle(bc)
