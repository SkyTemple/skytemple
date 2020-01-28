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

import gi

from skytemple.core.global_configuration import GlobalConfiguration
from skytemple.core.modules import Modules
from skytemple.core.task import AsyncTaskRunner

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

from gi.repository import Gtk, Gdk, GLib
from gi.repository.Gtk import Window
from skytemple.controller.main import MainController


def main():
    # TODO: Gtk.Application: https://python-gtk-3-tutorial.readthedocs.io/en/latest/application.html
    path = os.path.abspath(os.path.dirname(__file__))

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

    # Load event thread
    AsyncTaskRunner.instance()

    # Load configuration
    GlobalConfiguration.load()

    # Load modules
    Modules.load()

    # Load main window + controller
    MainController(builder, main_window)

    main_window.present()
    try:
        Gtk.main()
    except (KeyboardInterrupt, SystemExit):
        AsyncTaskRunner.end()


if __name__ == '__main__':
    main()
