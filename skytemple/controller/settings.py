#  Copyright 2020-2021 Capypara and the SkyTemple Contributors
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
import webbrowser
from functools import partial
from glob import glob

from gi.repository import Gtk, GLib

from skytemple.core.async_tasks.delegator import AsyncConfiguration
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.settings import SkyTempleSettingsStore
from skytemple_files.common.i18n_util import _

logger = logging.getLogger(__name__)
LANGS = [
    ('', _('Detect automatically')),
    ('C', _('English')),
    ('fr_FR.utf8', _('French')),
    ('de_DE.utf8', _('German')),
    ('pt_BR.utf8', _('Portuguese, Brazilian')),
    ('es_ES.utf8', _('Spanish')),
]


class SettingsController:
    """A dialog controller for UI settings."""
    def __init__(self, parent_window: Gtk.Window, builder: Gtk.Builder, settings: SkyTempleSettingsStore):
        self.window: Gtk.Window = builder.get_object('dialog_settings')
        self.window.set_transient_for(parent_window)
        self.window.set_attached_to(parent_window)
        self.parent_window = parent_window

        self.builder = builder
        self.settings = settings

        self.builder.get_object('setting_help_async').connect('clicked', self.on_setting_help_async_clicked)
        self.builder.get_object('setting_help_privacy').connect('activate-link', self.on_help_privacy_activate_link)

    def run(self):
        """
        Shows the settings dialog and processes settings changes. Doesn't return anything.
        """
        gtk_settings = Gtk.Settings.get_default()

        # Discord enabled state
        discord_enabled_previous = self.settings.get_integration_discord_enabled()
        settings_discord_enable = self.builder.get_object('setting_discord_enable')
        settings_discord_enable.set_active(discord_enabled_previous)

        # Gtk Theme
        if not sys.platform.startswith('linux'):
            store: Gtk.ListStore = Gtk.ListStore.new([str])
            cb: Gtk.ComboBox = self.builder.get_object('setting_gtk_theme')
            active = None
            for id, theme in enumerate(self._list_gtk_themes()):
                store.append([theme])
                if theme == gtk_settings.get_property("gtk-theme-name"):
                    active = id
            cb.set_model(store)
            if active is not None:
                cb.set_active(active)
        else:
            gbox: Gtk.Box = self.builder.get_object('setting_gtk_theme_box')
            for child in gbox:
                gbox.remove(child)
            label = Gtk.Label()
            label.set_markup(_("<i>Use System Settings to set this under Linux.</i>"))
            gbox.pack_start(label, False, False, 0)
            label.show()

        # Languages
        cb: Gtk.ComboBox = self.builder.get_object('setting_language')
        store: Gtk.ListStore = self.builder.get_object('lang_store')
        store.clear()
        active = None
        for id, (code, name) in enumerate(LANGS):
            store.append([code, name])
            if code == self.settings.get_locale():
                active = id
        if active is not None:
            cb.set_active(active)

        # Async modes
        cb: Gtk.ComboBox = self.builder.get_object('setting_async')
        store: Gtk.ListStore = self.builder.get_object('async_store')
        store.clear()
        active = None
        for mode in AsyncConfiguration:
            if mode.available():
                store.append([mode.value, mode.name_localized])
                if mode == self.settings.get_async_configuration():
                    active = mode.value
        if active is not None:
            cb.set_active_id(active)

        # Sentry
        allow_sentry_previous = self.settings.get_integration_discord_enabled()
        settings_allow_sentry_enable = self.builder.get_object('setting_allow_sentry')
        settings_allow_sentry_enable.set_active(allow_sentry_previous)

        response = self.window.run()

        have_to_restart = False
        if response == Gtk.ResponseType.ACCEPT:

            # Discord enabled state
            discord_enabled = settings_discord_enable.get_active()
            if discord_enabled != discord_enabled_previous:
                self.settings.set_integration_discord_enabled(discord_enabled)
                have_to_restart = True

            # Gtk Theme
            if not sys.platform.startswith('linux'):
                cb: Gtk.ComboBox = self.builder.get_object('setting_gtk_theme')
                iter = cb.get_active_iter()
                if (iter != None):
                    theme_name = cb.get_model()[iter][0]
                    gtk_settings.set_property("gtk-theme-name", theme_name)
                    self.settings.set_gtk_theme(theme_name)

            # Languages
            cb: Gtk.ComboBox = self.builder.get_object('setting_language')
            lang_name = cb.get_model()[cb.get_active_iter()][0]
            before = self.settings.get_locale()
            if before != lang_name:
                self.settings.set_locale(lang_name)
                have_to_restart = True

            # Async modes
            cb: Gtk.ComboBox = self.builder.get_object('setting_async')
            async_mode = AsyncConfiguration(cb.get_model()[cb.get_active_iter()][0])
            before = self.settings.get_async_configuration()
            if before != async_mode:
                self.settings.set_async_configuration(async_mode)
                have_to_restart = True

            # Sentry
            allow_sentry_enabled = settings_allow_sentry_enable.get_active()
            if allow_sentry_enabled != allow_sentry_previous:
                self.settings.set_allow_sentry(allow_sentry_enabled)
                if not allow_sentry_enabled:
                    have_to_restart = True
                else:
                    from skytemple.core import sentry
                    sentry.init()

        self.window.hide()

        if have_to_restart:
            md = SkyTempleMessageDialog(self.parent_window,
                                        Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                        Gtk.ButtonsType.OK, _("You need to restart SkyTemple to "
                                                              "apply some of the settings."),
                                        title="SkyTemple")
            md.run()
            md.destroy()

    def on_setting_help_native_enable_clicked(self, *args):
        md = SkyTempleMessageDialog(
            self.window,
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("If this is enabled a new and faster (but slightly experimental) codebase is "
              "used to load and manipulate game files. Try to disable this if you run into "
              "crashes or other issues.")
        )
        md.run()
        md.destroy()

    def on_setting_help_async_clicked(self, *args):
        md = SkyTempleMessageDialog(
            self.window,
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("This changes the way SkyTemple behaves when asynchronous operations are done "
              "(eg. loading files and views). You usually don't want to change this, "
              "unless you know what you are doing or are running into crashes or other issues.\n\n\n"
              "Thread-based: SkyTemple spawns an extra thread to run asynchronous operations. "
              "This could lead to thread safety issues, but is the 'smoothest' loading experience.\n\n"
              "Synchronous: Asynchronous operations run immediately. The SkyTemple UI freezes briefly during that.\n\n"
              "GLib: Same has 'Synchronous' but the UI gets the chance to finish displaying loaders etc. "
              "before they are run.\n\n"
              "Using Gbulb event loop: This enables Single-Thread asynchronous loading. It is generally the preferred"
              "option if available.")
        )
        md.run()
        md.destroy()

    def on_help_privacy_activate_link(self, *args):
        webbrowser.open_new_tab("https://skytemple.org/privacy.html")

    def _list_gtk_themes(self):
        dirs = [
            Gtk.rc_get_theme_dir(),
            os.path.join(GLib.get_user_data_dir(), 'themes'),
            os.path.join(GLib.get_home_dir(), '.themes')
        ]
        for dir in GLib.get_system_data_dirs():
            dirs.append(os.path.join(dir, 'themes'))

        themes = set()
        for dir in dirs:
            for f in glob(os.path.join(dir, '*', 'index.theme')):
                themes.add(f.split(os.path.sep)[-2])

        return themes
