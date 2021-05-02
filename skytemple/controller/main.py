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

import os
import sys
import traceback
import webbrowser
from threading import current_thread
from typing import Optional
import packaging.version

import gi
import logging

from gi.repository.GdkPixbuf import Pixbuf

from skytemple.controller.settings import SettingsController
from skytemple.controller.tilequant import TilequantController
from skytemple.core.abstract_module import AbstractModule
from skytemple.core.controller_loader import load_controller
from skytemple.core.error_handler import display_error
from skytemple.core.events.events import EVT_VIEW_SWITCH, EVT_PROJECT_OPEN
from skytemple.core.events.manager import EventManager
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.module_controller import AbstractController
from skytemple.core.rom_project import RomProject
from skytemple.core.settings import SkyTempleSettingsStore
from skytemple.core.ssb_debugger.manager import DebuggerManager
from skytemple_files.common.project_file_manager import ProjectFileManager
from skytemple_files.common.task_runner import AsyncTaskRunner
from skytemple.core.ui_utils import add_dialog_file_filters, recursive_down_item_store_mark_as_modified, data_dir, \
    version, open_dir
from skytemple_files.common.i18n_util import _, f
from skytemple_files.common.version_util import check_newest_release, ReleaseType, get_event_banner

gi.require_version('Gtk', '3.0')

from gi.repository import Gtk, Gdk, GLib, Gio
from gi.repository.Gtk import *

main_thread = current_thread()
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
COL_VISIBLE = 7
DISCORD_INVITE_LINK = 'https://discord.gg/skytemple'


class MainController:

    _instance: 'MainController' = None

    @classmethod
    def window(cls):
        """Utility method to get main window from modules"""
        return cls._instance.window

    @classmethod
    def debugger_manager(cls) -> DebuggerManager:
        """Utility method to get debugger manager from modules"""
        return cls._instance._debugger_manager

    @classmethod
    def reload_view(cls):
        cls._instance.load_view(cls._instance._last_selected_view_model, cls._instance._last_selected_view_iter,
                                cls._instance._main_item_list)

    def __init__(self, builder: Builder, window: Window, settings: SkyTempleSettingsStore):
        self.builder = builder
        self.window = window
        self.__class__._instance = self

        self.settings = settings
        self.recent_files = self.settings.get_recent_files()

        self._load_support_images()

        # Created on demand
        self._loading_dialog: Dialog = None
        self._main_item_list: TreeView = None
        self._main_item_filter: TreeModel = None
        self._last_selected_view_model = None
        self._last_selected_view_iter = None

        self._recent_files_store: ListStore = self.builder.get_object('recent_files_store')
        self._item_store: TreeStore = builder.get_object('item_store')
        self._editor_stack: Stack = builder.get_object('editor_stack')

        builder.connect_signals(self)
        window.connect("destroy", self.on_destroy)

        self._search_text = None
        self._current_view_module = None
        self._current_view_controller_class = None
        self._current_view_item_id = None
        self._resize_timeout_id = None
        self._loaded_map_bg_module = None
        self._current_breadcrumbs = []

        if not sys.platform.startswith('darwin'):
            # Don't load the window position on macOS to prevent
            # the window from getting stuck on a disconnected screen
            self._load_position_and_size()

        self._configure_csd()
        self._load_icon()
        self._load_recent_files()
        self._connect_item_views()
        self._configure_error_view()
        self._check_for_updates()
        self._check_for_banner()

        self._debugger_manager = DebuggerManager()

        self.tilequant_controller = TilequantController(self.window, self.builder)
        self.settings_controller = SettingsController(self.window, self.builder, self.settings)

    def on_destroy(self, *args):
        logger.debug('Window destroyed. Ending task runner.')
        AsyncTaskRunner.end()
        Gtk.main_quit()
        self._debugger_manager.destroy()

    def on_main_window_delete_event(self, *args):
        if not self._debugger_manager.close():
            # Cancel
            return True
        rom = RomProject.get_current()
        if rom is not None and rom.has_modifications():
            response = self._show_are_you_sure(rom)
            if response == 0:
                return False
            elif response == 1:
                # Save (True on success, False on failure. Don't close the file if we can't save it...)
                self._save()
                # TODO: we just cancel atm, because the saving is done async. It would probably be nice to also
                #       exit, when it's done without error
                return True
            else:
                # Cancel
                return True
        return False

    def on_intro_dialog_close(self, assistant: Gtk.Assistant, *args):
        self.settings.set_assistant_shown(True)
        assistant.hide()

    def on__enter_notify_event__pointer(self, w: Gtk.Widget, evt: Gdk.EventCrossing):
        w.get_window().set_cursor(Gdk.Cursor.new_from_name(w.get_display(), 'pointer'))

    def on__leave_notify_event__pointer(self, w: Gtk.Widget, evt: Gdk.EventCrossing):
        w.get_window().set_cursor(Gdk.Cursor.new_from_name(w.get_display(), 'default'))

    def on_discord_icon_container_button_release_event(self, w: Gtk.Widget, evt: Gdk.Event):
        if evt.button == 1:
            webbrowser.open(DISCORD_INVITE_LINK)

    def on_button_support_us_clicked(self, *args):
        diag = self.builder.get_object('suppot_us_dialog')
        diag.run()
        diag.hide()

    def on_suppot_us_discord_container_button_release_event(self, w: Gtk.Widget, evt: Gdk.Event):
        if evt.button == 1:
            webbrowser.open(DISCORD_INVITE_LINK)

    def on_suppot_us_github_container_button_release_event(self, w: Gtk.Widget, evt: Gdk.Event):
        if evt.button == 1:
            webbrowser.open("https://github.com/SkyTemple")

    def on_suppot_us_kofi_parakoopa_container_button_release_event(self, w: Gtk.Widget, evt: Gdk.Event):
        if evt.button == 1:
            webbrowser.open("https://ko-fi.com/parakoopa")

    def on_suppot_us_kofi_psy_container_button_release_event(self, w: Gtk.Widget, evt: Gdk.Event):
        if evt.button == 1:
            webbrowser.open("https://ko-fi.com/psycomm")

    def on_key_press_event(self, wdg, event):
        ctrl = (event.state & Gdk.ModifierType.CONTROL_MASK)

        if ctrl and event.keyval == Gdk.KEY_s and RomProject.get_current() is not None:
            self._save()

    def on_save_button_clicked(self, wdg):
        self._save()

    def on_reload_button_clicked(self, wdg):
        if RomProject.get_current().filename:
            self._open_file(RomProject.get_current().filename)

    def on_debugger_button_clicked(self, wdg):
        self._debugger_manager.open(self.window)

    def on_save_as_button_clicked(self, wdg):
        project = RomProject.get_current()

        dialog = Gtk.FileChooserNative.new(
            "Save As...",
            self.window,
            Gtk.FileChooserAction.SAVE,
            None, None
        )
        dialog.set_filename(project.filename)

        add_dialog_file_filters(dialog)

        response = dialog.run()
        fn = dialog.get_filename()
        if '.' not in fn:
            fn += '.nds'
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            project.filename = fn
            self._save(True)
            project.get_rom_module().update_filename()
            self._update_recent_files(fn)

    def on_open_more_clicked(self, button: Button):
        """Dialog to open a file"""
        dialog = Gtk.FileChooserNative.new(
            _("Open ROM..."),
            self.window,
            Gtk.FileChooserAction.OPEN,
            None, None
        )

        add_dialog_file_filters(dialog)

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            self._open_file(fn)

    def on_open_tree_selection_changed(self, selection: TreeSelection):
        """Open a file selected in a tree"""
        model, treeiter = selection.get_selected()
        if treeiter is not None and model is not None:
            self._open_file(model[treeiter][0])
            self.builder.get_object('open_menu').hide()

    def on_main_window_configure_event(self, *args):
        """Save the window size and position to the settings store"""
        # We delay handling this, to make sure we only handle it when the user is done resizing/moving.
        if self._resize_timeout_id is not None:
            GLib.source_remove(self._resize_timeout_id)
        self._resize_timeout_id = GLib.timeout_add_seconds(1, self.on_main_window_configure_event__handle)

    def on_main_window_configure_event__handle(self):
        self.settings.set_window_position(self.window.get_position())
        self.settings.set_window_size(self.window.get_size())
        self._resize_timeout_id = None

    def on_main_window_state_event(self, w: Gtk.Window, evt: Gdk.EventWindowState):
        if evt.changed_mask & Gdk.WindowState.FOCUSED:
            if evt.new_window_state & Gdk.WindowState.FOCUSED:
                EventManager.instance().main_window_has_focus()
            else:
                EventManager.instance().main_window_lost_focus()

    def on_file_opened(self):
        """Update the UI after a ROM file has been opened."""
        assert current_thread() == main_thread
        logger.debug('File opened.')
        # Init the sprite provider
        RomProject.get_current().get_sprite_provider().init_loader(self.window.get_screen())

        self._init_window_after_rom_load(os.path.basename(RomProject.get_current().filename))
        try:
            # Load root node, ROM
            project = RomProject.get_current()
            rom_module = project.get_rom_module()
            rom_module.load_rom_data()
            
            # Initialize patch-specific properties for this rom project
            project.init_patch_properties()
            
            logger.info(f'Loaded ROM {project.filename} ({rom_module.get_static_data().game_edition})')
            logger.debug(f"Loading ROM module tree items...")
            rom_module.load_tree_items(self._item_store, None)
            root_node = rom_module.get_root_node()

            
            # Tell the debugger
            self._debugger_manager.handle_project_change()

            # Load item tree items
            for module in sorted(project.get_modules(False), key=lambda m: m.sort_order()):
                logger.debug(f"Loading {module.__class__.__name__} module tree items...")
                module.load_tree_items(self._item_store, root_node)
                if module.__class__.__name__ == 'MapBgModule':
                    self._loaded_map_bg_module = module
            # TODO: Load settings from ROM for history, bookmarks, etc? - separate module?
            logger.debug(f"Loaded all modules.")

            # Trigger event
            EventManager.instance().trigger(EVT_PROJECT_OPEN, project=project)

            # Select & load main ROM item by default
            selection: TreeSelection = self._main_item_list.get_selection()
            selection.select_path(self._item_store.get_path(root_node))
            self.load_view(self._item_store, root_node, self._main_item_list)
        except BaseException as ex:
            self.on_file_opened_error(sys.exc_info(), ex)
            return

        if self._loading_dialog is not None:
            self._loading_dialog.hide()
            self._loading_dialog = None

        # Show the initial assistant window
        if not self.settings.get_assistant_shown():
            self.on_settings_show_assistant_clicked()

    def on_file_opened_error(self, exc_info, exception):
        """Handle errors during file openings."""
        assert current_thread() == main_thread
        logger.error('Error on file open.', exc_info=exception)
        if self._loading_dialog is not None:
            self._loading_dialog.hide()
            self._loading_dialog = None
        display_error(
            exc_info,
            str(exception),
            _("Error opening the ROM")
        )

    def on_file_saved(self):
        if self._loading_dialog is not None:
            self._loading_dialog.hide()
            self._loading_dialog = None

        rom = RomProject.get_current()
        self._set_title(os.path.basename(rom.filename), False)
        recursive_down_item_store_mark_as_modified(self._item_store[self._item_store.get_iter_first()], False)

    def on_file_saved_error(self, exc_info, exception):
        """Handle errors during file saving."""
        logger.error('Error on save open.', exc_info=exception)

        if self._loading_dialog is not None:
            self._loading_dialog.hide()
            self._loading_dialog = None
        display_error(
            exc_info,
            str(exception),
            _("Error saving the ROM")
        )

    def on_main_item_list_button_press_event(self, tree: TreeView, event: Gdk.Event):
        """Handle click on item: Switch view"""
        assert current_thread() == main_thread
        if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS:
            model, treeiter = tree.get_selection().get_selected()
            if model is not None and treeiter is not None and RomProject.get_current() is not None:
                self.load_view(model, treeiter, tree, False)

    def load_view_main_list(self, treeiter: Gtk.TreeIter):
        return self.load_view(self._item_store, treeiter, self._main_item_list)

    def load_view(self, model: Gtk.TreeModel, treeiter: Gtk.TreeIter, tree: Gtk.TreeView, scroll_into_view=True):
        logger.debug('View selected. Locking and showing Loader.')
        path = model.get_path(treeiter)
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
        # Expand the node
        tree.expand_to_path(path)
        # Select node
        tree.get_selection().select_path(path)
        # Scroll node into view
        if scroll_into_view:
            tree.scroll_to_cell(path, None, True, 0.5, 0.5)
        self._last_selected_view_model = model
        self._last_selected_view_iter = treeiter

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
        EventManager.instance().trigger(EVT_VIEW_SWITCH, module=module, controller=controller,
                                        breadcrumbs=self._current_breadcrumbs)

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
        self._search_text = search.get_text().strip()
        self._filter__refresh_results()

    def on_settings_show_assistant_clicked(self, *args):
        assistant: Gtk.Assistant = self.builder.get_object('intro_dialog')
        assistant.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        assistant.commit()
        assistant.set_transient_for(self.window)
        assistant.set_attached_to(self.window)
        assistant.show_all()

    def on_settings_open_settings_clicked(self, *args):
        self.settings_controller.run()

    def on_intro_dialog_created_with_clicked(self, *args):
        if RomProject.get_current() is None or self._loaded_map_bg_module is None:
            md = SkyTempleMessageDialog(MainController.window(),
                                        Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                                        Gtk.ButtonsType.OK, _("A project must be opened to use this."))
            md.set_position(Gtk.WindowPosition.CENTER)
            md.run()
            md.destroy()
            return
        self._loaded_map_bg_module.add_created_with_logo()

    def on_settings_dir_clicked(self, *args):
        open_dir(ProjectFileManager.shared_config_dir())

    def on_settings_about_clicked(self, *args):
        about: Gtk.AboutDialog = self.builder.get_object("about_dialog")
        about.connect("response", lambda d, r: d.hide())

        def activate_link(l, uri, *args):
            webbrowser.open_new_tab(uri)
            return True

        about.connect("activate-link", activate_link)
        header_bar: Optional[Gtk.HeaderBar] = about.get_header_bar()
        if header_bar is not None:
            # Cool bug??? And it only works on the left as well, wtf?
            header_bar.set_decoration_layout('close')
        about.set_version(version())
        about.run()

    def on_update_button_clicked(self, *args):
        webbrowser.open_new_tab("https://projectpokemon.org/home/files/file/4193-skytemple-pmd2-rom-edtior/")

    def gtk_widget_hide_on_delete(self, w: Gtk.Widget, *args):
        w.hide_on_delete()
        return True

    @classmethod
    def show_tilequant_dialog(cls, num_pals=16, num_colors=16):
        cls._instance.tilequant_controller.run(num_pals, num_colors)

    def _load_position_and_size(self):
        # Load window sizes
        window_size = self.settings.get_window_size()
        if window_size is not None:
            self.window.resize(*window_size)
        window_position = self.settings.get_window_position()
        if window_position is not None:
            self.window.move(*window_position)

    def _configure_csd(self):
        tb: Gtk.HeaderBar = self.window.get_titlebar()
        # On macOS, the buttons need to be on the left.
        if sys.platform.startswith('darwin'):
            tb.set_decoration_layout("close,minimize,maximize,menu:")
        # TODO. Following code disables CSD.
        return
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
        recent_file_list = self.recent_files

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
            self.builder.get_object('open_more').set_label(_("Open a ROM"))
            self.builder.get_object('open_more_main').set_label(_("Open a ROM"))
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
            # noinspection PyUnusedLocal
            rom_name = os.path.basename(filename)
            self.builder.get_object('file_opening_dialog_label').set_label(
                f(_('Loading ROM "{rom_name}"...'))
            )
            logger.debug(f(_('Opening {filename}.')))
            RomProject.open(filename, self)
            # Add to the list of recent files and save
            self._update_recent_files(filename)
            # Show loading spinner
            self._loading_dialog.run()

    def _check_open_file(self):
        """Check for open files, and ask the user what to do. Returns false if they cancel."""
        rom = RomProject.get_current()
        if not self._debugger_manager.check_save():
            # Cancel
            return False
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
        self._main_item_filter.set_visible_column(COL_VISIBLE)

        # TODO: Recent and Favorites

    # TODO: CODE DUPLICATION BETWEEN SKYTEMPLE AND SSB DEBUGGER -- If we ever make a common package, this must go into it!
    def _filter__refresh_results(self):
        """Filter the main item view"""
        if self._search_text == "":
            self._item_store.foreach(self._filter__reset_row, True)
        else:
            self._main_item_list.collapse_all()
            self._item_store.foreach(self._filter__reset_row, False)
            self._item_store.foreach(self._filter__show_matches)
            self._main_item_filter.foreach(self._filter__expand_all_visible)

    def _filter__reset_row(self, model, path, iter, make_visible):
        """Change the visibility of the given row"""
        self._item_store[iter][COL_VISIBLE] = make_visible

    def _filter__make_path_visible(self, model, iter):
        """Make a row and its ancestors visible"""
        while iter:
            self._item_store[iter][COL_VISIBLE] = True
            iter = model.iter_parent(iter)

    def _filter__make_subtree_visible(self, model, iter):
        """Make descendants of a row visible"""
        for i in range(model.iter_n_children(iter)):
            subtree = model.iter_nth_child(iter, i)
            if model[subtree][COL_VISIBLE]:
                # Subtree already visible
                continue
            self._item_store[subtree][COL_VISIBLE] = True
            self._filter__make_subtree_visible(model, subtree)

    def _filter__expand_all_visible(self, model: Gtk.TreeStore, path, iter):
        """
        This is super annoying. Because of the two different "views" on the model,
        we can't do this in show_matches, because we have to use the filter model here!
        """
        search_query = self._search_text.lower()
        text = model[iter][1].lower()
        if search_query in text:
            self._main_item_list.expand_to_path(path)

    def _filter__show_matches(self, model: Gtk.TreeStore, path, iter):
        search_query = self._search_text.lower()
        text = model[iter][1].lower()
        if search_query in text:
            # Propagate visibility change up
            self._filter__make_path_visible(model, iter)
            # Propagate visibility change down
            self._filter__make_subtree_visible(model, iter)
    # END CODE DUPLICATION

    def _configure_error_view(self):
        sw: ScrolledWindow = self.builder.get_object('es_error_text_sw')
        sw.set_min_content_width(200)
        sw.set_min_content_height(300)

    def _init_window_after_rom_load(self, rom_name):
        """Set the titlebar and make buttons sensitive after a ROM load"""
        self._item_store.clear()
        self.builder.get_object('save_button').set_sensitive(True)
        self.builder.get_object('reload_button').set_sensitive(True)
        self.builder.get_object('save_as_button').set_sensitive(True)
        self.builder.get_object('main_item_list_search').set_sensitive(True)
        self.builder.get_object('debugger_button').set_sensitive(True)
        # TODO: Titlebar for Non-CSD situation
        self._set_title(rom_name, False)

    def _init_window_before_view_load(self, node: TreeModelRow):
        """Update the subtitle / breadcrumb before switching views"""
        try:
            bc = ""
            parent = node
            bc_array = []
            while parent:
                bc = f" > {parent[6]}" + bc
                bc_array.append(parent[6])
                parent = parent.parent
            bc = bc[3:]
            self._current_breadcrumbs = bc_array
            self.window.get_titlebar().set_subtitle(bc)

            # Check if files are modified
            if RomProject.get_current().has_modifications():
                self._set_title(os.path.basename(RomProject.get_current().filename), True)
        except BaseException as ex:
            logger.warning("Failed updating window titles.", exc_info=ex)

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
            # noinspection PyUnusedLocal
            rom_name = os.path.basename(rom.filename)
            self.builder.get_object('file_opening_dialog_label').set_label(
                f(_('Saving ROM "{rom_name}"...'))
            )
            logger.debug(f(_('Saving {rom.filename}.')))

            # This will trigger a signal.
            rom.save(self)
            self._loading_dialog.run()

    def _show_are_you_sure(self, rom):
        # noinspection PyUnusedLocal
        rom_name = os.path.basename(rom.filename)
        dialog: MessageDialog = SkyTempleMessageDialog(
            self.window,
            Gtk.DialogFlags.MODAL,
            Gtk.MessageType.WARNING,
            Gtk.ButtonsType.NONE, f(_("Do you want to save changes to {rom_name}?"))
        )
        dont_save: Widget = dialog.add_button(_("Don't Save"), 0)
        dont_save.get_style_context().add_class('destructive-action')
        dialog.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(_("Save"), 1)
        dialog.format_secondary_text(_("If you don't save, your changes will be lost."))
        response = dialog.run()
        dialog.destroy()
        return response

    def _load_support_images(self):
        # Load the support us images
        try:
            # Discord
            image = Gtk.Image()
            image.show()
            image.set_from_file(os.path.join(data_dir(), "discord.png"))
            self.builder.get_object('suppot_us_discord_container').add(image)
            # Github
            image = Gtk.Image()
            image.show()
            image.set_from_file(os.path.join(data_dir(), "github.png"))
            self.builder.get_object('suppot_us_github_container').add(image)
            # Kofi
            image = Gtk.Image()
            image.show()
            image.set_from_file(os.path.join(data_dir(), "kofi.png"))
            self.builder.get_object('suppot_us_kofi_parakoopa_container').add(image)
            # Kofi 2
            image = Gtk.Image()
            image.show()
            image.set_from_file(os.path.join(data_dir(), "kofi.png"))
            self.builder.get_object('suppot_us_kofi_psy_container').add(image)
        except BaseException:
            # We are not crashing over some images...
            pass

    def _update_recent_files(self, fn):
        new_recent_files = []
        for rf in self.recent_files:
            if rf != fn and rf not in new_recent_files:
                new_recent_files.append(rf)
        new_recent_files.insert(0, fn)
        self.recent_files = new_recent_files
        self.settings.set_recent_files(self.recent_files)
        # TODO Update recent files store too!

    def _check_for_updates(self):
        try:
            new_version = check_newest_release(ReleaseType.SKYTEMPLE)
            if packaging.version.parse(version()) < packaging.version.parse(new_version):
                self.builder.get_object('update_new_version').set_text(new_version)
                return
        except Exception:
            pass
        # else/except:
        self.builder.get_object('update_info').hide()

    def _check_for_banner(self):
        try:
            img_banner, url = get_event_banner()
            if img_banner is not None:
                input_stream = Gio.MemoryInputStream.new_from_data(img_banner, None)
                pixbuf = Pixbuf.new_from_stream(input_stream, None)
                image = Gtk.Image()
                image.show()
                image.set_from_pixbuf(pixbuf)

                def open_web(*args):
                    webbrowser.open_new_tab(url)

                def cursor_change(w: Gtk.Widget, evt: Gdk.EventCrossing):
                    cursor = None
                    if evt.get_event_type() == Gdk.EventType.ENTER_NOTIFY:
                        cursor = Gdk.Cursor.new_from_name(w.get_display(), "pointer")
                    elif evt.get_event_type() == Gdk.EventType.LEAVE_NOTIFY:
                        cursor = Gdk.Cursor.new_from_name(w.get_display(), "default")
                    if cursor:
                        w.get_window().set_cursor(cursor)
                b_info = self.builder.get_object('banner_info')
                b_info.connect('button-release-event', open_web)
                b_info.connect('enter-notify-event', cursor_change)
                b_info.connect('leave-notify-event', cursor_change)
                b_info.add_events(Gdk.EventMask.BUTTON_RELEASE_MASK)
                b_info.add(image)
                return
        except Exception:
            pass
        # else/except:
        self.builder.get_object('banner_info').hide()
