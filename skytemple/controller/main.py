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

import os
import traceback
from threading import current_thread

import gi
import logging

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.controller_loader import load_controller
from skytemple.core.module_controller import AbstractController
from skytemple.core.rom_project import RomProject
from skytemple.core.task_runner import AsyncTaskRunner
from skytemple.core.ui_utils import add_dialog_file_filters, recursive_down_item_store_mark_as_modified

gi.require_version('Gtk', '3.0')

from gi.repository import Gtk, Gdk
from gi.repository.Gtk import *
from gi.repository.GObject import GObject
main_thread = current_thread()
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class MainController:

    _main_window = None

    @classmethod
    def window(cls):
        """Utility method to get main window from modules"""
        return cls._main_window

    def __init__(self, builder: Builder, window: Window):
        self.builder = builder
        self.window = window
        self.__class__._main_window = window

        # Created on demand
        self._loading_dialog: Dialog = None
        self._main_item_list: TreeView = None
        self._main_item_filter: TreeModel = None

        self._recent_files_store: ListStore = self.builder.get_object('recent_files_store')
        self._item_store: TreeStore = builder.get_object('item_store')
        self._editor_stack: Stack = builder.get_object('editor_stack')

        builder.connect_signals(self)
        window.connect("destroy", self.on_destroy)

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

        ### DEBUG
        #self._open_file('/home/marco/austausch/dev/skytemple/skyworkcopy_edit.nds')

    def on_destroy(self, *args):
        logger.debug('Window destroyed. Ending task runner.')
        AsyncTaskRunner.end()
        Gtk.main_quit()

    def on_main_window_delete_event(self, *args):
        rom = RomProject.get_current()
        if rom is not None and rom.has_modifications():
            response = self._show_are_you_sure(rom)
            if response == 0:
                return False
            elif response == 1:
                # Save (True on success, False on failure. Don't close the file if we can't save it...)
                # TODO: NOT TRUE. We are using signals. This is broken right now!
                return not self._save()
            else:
                # Cancel
                return True
        return False

    def on_key_press_event(self, wdg, event):
        ctrl = (event.state & Gdk.ModifierType.CONTROL_MASK)

        if ctrl and event.keyval == Gdk.KEY_s and RomProject.get_current() is not None:
            self._save()

    def on_save_button_clicked(self, wdg):
        self._save()

    def on_save_as_button_clicked(self, wdg):
        project = RomProject.get_current()

        dialog = Gtk.FileChooserDialog(
            "Save As...",
            self.window,
            Gtk.FileChooserAction.SAVE,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        )
        dialog.set_filename(project.filename)

        add_dialog_file_filters(dialog)

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.OK:
            project.filename = fn
            self._save(True)

    def on_open_more_clicked(self, button: Button):
        """Dialog to open a file"""
        dialog = Gtk.FileChooserDialog(
            "Open ROM...",
            self.window,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        )

        add_dialog_file_filters(dialog)

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

    def on_file_opened(self):
        """Update the UI after a ROM file has been opened."""
        assert current_thread() == main_thread
        logger.debug('File opened.')

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
            self.on_file_opened_error(ex)
            return

        if self._loading_dialog is not None:
            self._loading_dialog.hide()
            self._loading_dialog = None

    def on_file_opened_error(self, exception):
        """Handle errors during file openings."""
        assert current_thread() == main_thread
        logger.debug('Error on file open.')
        if self._loading_dialog is not None:
            self._loading_dialog.hide()
            self._loading_dialog = None
        # TODO: Better exception display
        md = Gtk.MessageDialog(self.window,
                               Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                               Gtk.ButtonsType.OK, str(exception),
                               title="SkyTemple - Error!")
        md.set_position(Gtk.WindowPosition.CENTER)
        md.run()
        md.destroy()

    def on_file_saved(self):
        if self._loading_dialog is not None:
            self._loading_dialog.hide()
            self._loading_dialog = None

        rom = RomProject.get_current()
        self._set_title(os.path.basename(rom.filename), False)
        recursive_down_item_store_mark_as_modified(self._item_store[self._item_store.get_iter_first()], False)

    def on_file_saved_error(self, exception):
        """Handle errors during file saving."""
        logger.debug('Error on save open.')

        if self._loading_dialog is not None:
            self._loading_dialog.hide()
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
        assert current_thread() == main_thread
        model, treeiter = selection.get_selected()
        if model is not None and treeiter is not None and RomProject.get_current() is not None:
            logger.debug('View selected. Locking and showing Loader.')
            self._lock_trees()
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
                self
            ))

    def on_view_loaded(
            self, module: AbstractModule, controller: AbstractController, item_id: int
    ):
        """A new module view was loaded! Present it!"""
        assert current_thread() == main_thread
        # Check if current view still matches expected
        logger.debug('View loaded.')
        try:
            view = controller.get_view()
        except Exception as err:
            logger.debug("Error retreiving the loaded view")
            self.on_view_loaded_error(err)
            return
        if self._current_view_module != module or self._current_view_controller_class != controller.__class__ or self._current_view_item_id != item_id:
            logger.warning('Loaded view not matching selection.')
            view.destroy()
            return
        # Insert the view at page 3 [0,1,2,3] of the stack. If there is already a page, remove it.
        old_view = self._editor_stack.get_child_by_name('es__loaded_view')
        if old_view:
            logger.debug('Destroying old view...')
            self._editor_stack.remove(old_view)
            old_view.destroy()
        logger.debug('Adding and showing new view...')
        self._editor_stack.add_named(view, 'es__loaded_view')
        view.show_all()
        self._editor_stack.set_visible_child(view)
        logger.debug('Unlocking view trees.')
        self._unlock_trees()

    def on_view_loaded_error(self, ex: BaseException):
        """An error during module view load happened :("""
        assert current_thread() == main_thread
        logger.debug('View load error. Unlocking.')
        tb: TextBuffer = self.builder.get_object('es_error_text_buffer')
        tb.set_text(''.join(traceback.format_exception(etype=type(ex), value=ex, tb=ex.__traceback__)))
        self._editor_stack.set_visible_child(self.builder.get_object('es_error'))
        self._unlock_trees()

    def on_item_store_row_changed(self, model, path, iter):
        """Update the window title for the current selected tree model row if it changed"""
        if model is not None and iter is not None:
            selection_model, selection_iter = self._main_item_list.get_selection().get_selected()
            if selection_model is not None and selection_iter is not None:
                if selection_model[selection_iter].path == path:
                    self._init_window_before_view_load(model[iter])

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
            logger.debug(f'Opening {filename}.')
            RomProject.open(filename, self)
            self._loading_dialog.run()

    def _check_open_file(self):
        """Check for open files, and ask the user what to do. Returns false if they cancel."""
        rom = RomProject.get_current()
        if rom is not None and rom.has_modifications():
            response = self._show_are_you_sure(rom)

            if response == 0:
                # Don't save
                return True
            elif response == 1:
                # Save (True on success, False on failure. Don't close the file if we can't save it...)
                # TODO: NOT TRUE. We are using signals. This is broken right now!
                return self._save()
            else:
                # Cancel
                return False
        return True

    def _connect_item_views(self):
        """Connect the all items, recent items and favorite items views"""
        main_item_list: TreeView = self.builder.get_object('main_item_list')

        icon = Gtk.CellRendererPixbuf()
        title = Gtk.CellRendererText()
        column = TreeViewColumn("Title")

        column.pack_start(icon, True)
        column.pack_start(title, True)

        column.add_attribute(icon, "icon_name", 0)
        column.add_attribute(title, "text", 6)

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
        self._set_title(rom_name, False)

    def _init_window_before_view_load(self, node: TreeModelRow):
        """Update the subtitle / breadcrumb before switching views"""
        bc = ""
        parent = node
        while parent:
            bc = f" > {parent[6]}" + bc
            parent = parent.parent
        bc = bc[3:]
        self.window.get_titlebar().set_subtitle(bc)

        # Check if files are modified
        if RomProject.get_current().has_modifications():
            self._set_title(os.path.basename(RomProject.get_current().filename), True)

    def _set_title(self, rom_name, is_modified):
        # TODO: Titlebar for Non-CSD situation
        tb: HeaderBar = self.window.get_titlebar()
        tb.set_title(f"{'*' if is_modified else ''}{rom_name} (SkyTemple)")

    def _lock_trees(self):
        # TODO: Lock the other two!
        self._main_item_list.set_sensitive(False)

    def _unlock_trees(self):
        # TODO: Unlock the other two!
        self._main_item_list.set_sensitive(True)

    def _save(self, force=False):
        rom = RomProject.get_current()

        if rom.has_modifications() or force:
            self._loading_dialog = self.builder.get_object('file_opening_dialog')
            self.builder.get_object('file_opening_dialog_label').set_label(
                f'Saving ROM "{os.path.basename(rom.filename)}"...'
            )
            logger.debug(f'Saving {rom.filename}.')

            # This will trigger a signal.
            rom.save(self)
            self._loading_dialog.run()

    def _show_are_you_sure(self, rom):
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
        return response

