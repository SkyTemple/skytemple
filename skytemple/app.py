#  Copyright 2020-2023 Capypara and the SkyTemple Contributors
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

from gi.repository import Gtk, Gdk, GLib
from skytemple.controller.main import MainController
from skytemple.core.events.manager import EventManager
from skytemple.core.modules import Modules
from skytemple.core.profiling import record_transaction, record_span
from skytemple.core.settings import SkyTempleSettingsStore
from skytemple.core.ui_utils import data_dir, builder_get_assert, make_builder
from skytemple_icons import icons
from skytemple_ssb_debugger.main import get_debugger_data_dir


class SkyTempleApplication(Gtk.Application):
    def __init__(self, path: str, settings: SkyTempleSettingsStore):
        with record_transaction("__start"):
            with record_span("sys", "load-theme"):
                if sys.platform.startswith("win"):
                    # Load theming under Windows
                    _load_theme(settings)
                    # Solve issue #12
                    try:
                        from skytemple_files.common.platform_utils.win import (
                            win_set_error_mode,
                        )

                        win_set_error_mode()
                    except BaseException:
                        # This really shouldn't fail, but it's not important enough to crash over
                        pass

                if sys.platform.startswith("darwin"):
                    # Load theming under macOS
                    _load_theme(settings)

                    # The search path is wrong if SkyTemple is executed as an .app bundle
                    if getattr(sys, "frozen", False):
                        path = os.path.dirname(sys.executable)

                itheme: Gtk.IconTheme = Gtk.IconTheme.get_default()
                itheme.append_search_path(os.path.abspath(icons()))  # type: ignore
                itheme.append_search_path(
                    os.path.abspath(os.path.join(data_dir(), "icons"))
                )
                itheme.append_search_path(
                    os.path.abspath(os.path.join(get_debugger_data_dir(), "icons"))
                )
                itheme.rescan_if_needed()

            with record_span("sys", "load-builder"):
                # Load Builder and Window
                builder = make_builder(os.path.join(path, "skytemple.glade"))
                self.main_window = builder_get_assert(
                    builder, Gtk.ApplicationWindow, "main_window"
                )
                GLib.set_application_name("SkyTemple")

            with record_span("sys", "load-css"):
                # Load CSS
                style_provider = Gtk.CssProvider()
                with open(os.path.join(path, "skytemple.css"), "rb") as f:
                    css = f.read()
                style_provider.load_from_data(css)
                default_screen = Gdk.Screen.get_default()
                if default_screen is not None:
                    Gtk.StyleContext.add_provider_for_screen(
                        default_screen,
                        style_provider,
                        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
                    )

            with record_span("sys", "init-events"):
                # Init. core events
                event_manager = EventManager.instance()
                if settings.get_integration_discord_enabled():
                    try:
                        from skytemple.core.events.impl.discord import DiscordPresence

                        discord_listener = DiscordPresence()
                        event_manager.register_listener(discord_listener)
                    except BaseException as exc:
                        logging.warning(
                            "Error setting up Discord integration:", exc_info=exc
                        )

            with record_span("sys", "load-modules"):
                # Load modules
                Modules.load(settings)

            with record_span("sys", "load-main-controller"):
                # Load main window + controller
                MainController(builder, self.main_window, settings)
        super().__init__(application_id="org.skytemple.SkyTemple")

    def do_activate(self) -> None:
        self.main_window.set_application(self)
        self.main_window.set_icon_name("skytemple")
        self.main_window.present()


def _load_theme(settings: SkyTempleSettingsStore):
    gtk_settings = Gtk.Settings.get_default()
    if gtk_settings is not None:
        gtk_settings.set_property(
            "gtk-theme-name", settings.get_gtk_theme(default="Arc-Dark")
        )
