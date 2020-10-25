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
import logging
import os
import sys

import gi

from skytemple.core.events.manager import EventManager
from skytemple.core.modules import Modules
from skytemple.core.settings import SkyTempleSettingsStore
from skytemple.core.ui_utils import data_dir
from skytemple_files.common.task_runner import AsyncTaskRunner
from skytemple_icons import icons
from skytemple_ssb_debugger.main import get_debugger_data_dir

gi.require_version('Gtk', '3.0')
try:
    gi.require_foreign("cairo")
except ImportError:
    from gi.repository import Gtk

    md = Gtk.MessageDialog(None,
                           Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                           Gtk.ButtonsType.OK, "PyGObject compiled without Cairo support. Can't start!",
                           title="SkyTemple - Error!")
    md.set_position(Gtk.WindowPosition.CENTER)
    md.run()
    md.destroy()
    exit(1)

from gi.repository import Gtk, Gdk, GLib, Gio
from gi.repository.Gtk import Window
from skytemple.controller.main import MainController


def main():
    # TODO: Gtk.Application: https://python-gtk-3-tutorial.readthedocs.io/en/latest/application.html
    path = os.path.abspath(os.path.dirname(__file__))

    # Load settings
    settings = SkyTempleSettingsStore()

    if sys.platform.startswith('win'):
        # Load theming under Windows
        _windows_load_theme(settings)
        # Solve issue #12
        try:
            from skytemple_files.common.platform_utils.win import win_set_error_mode
            win_set_error_mode()
        except BaseException:
            # This really shouldn't fail, but it's not important enough to crash over
            pass

    if sys.platform.startswith('darwin'):
        # Load theming under macOS
        _macos_load_theme(settings)

    itheme: Gtk.IconTheme = Gtk.IconTheme.get_default()
    itheme.append_search_path(os.path.abspath(icons()))
    itheme.append_search_path(os.path.abspath(os.path.join(data_dir(), "icons")))
    itheme.append_search_path(os.path.abspath(os.path.join(get_debugger_data_dir(), "icons")))
    itheme.rescan_if_needed()

    # Load Builder and Window
    builder = Gtk.Builder()
    builder.add_from_file(os.path.join(path, "skytemple.glade"))
    main_window: Window = builder.get_object("main_window")
    main_window.set_role("SkyTemple")
    GLib.set_application_name("SkyTemple")
    GLib.set_prgname("skytemple")
    # TODO: Deprecated but the only way to set the app title on GNOME...?
    main_window.set_wmclass("SkyTemple", "SkyTemple")

    # Load CSS
    style_provider = Gtk.CssProvider()
    with open(os.path.join(path, "skytemple.css"), 'rb') as f:
        css = f.read()
    style_provider.load_from_data(css)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), style_provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

    # Load async task runner thread
    AsyncTaskRunner.instance()

    # Init. core events
    event_manager = EventManager.instance()
    if settings.get_integration_discord_enabled():
        try:
            from skytemple.core.events.impl.discord import DiscordPresence
            discord_listener = DiscordPresence()
            event_manager.register_listener(discord_listener)
        except BaseException:
            pass

    # Load modules
    Modules.load()

    # Load main window + controller
    MainController(builder, main_window, settings)

    main_window.present()
    main_window.set_icon_name('skytemple')
    try:
        Gtk.main()
    except (KeyboardInterrupt, SystemExit):
        AsyncTaskRunner.end()


def _windows_load_theme(settings: SkyTempleSettingsStore):
    gtk_settings = Gtk.Settings.get_default()
    gtk_settings.set_property("gtk-theme-name", settings.get_gtk_theme(default='Arc-Dark'))


def _macos_load_theme(settings: SkyTempleSettingsStore):
    gtk_settings = Gtk.Settings.get_default()
    gtk_settings.set_property("gtk-theme-name", settings.get_gtk_theme(default='Mojave-dark'))


if __name__ == '__main__':
    # TODO: At the moment doesn't support any cli arguments.
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    main()
