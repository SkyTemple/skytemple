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
import logging
import os
import sys
from functools import partial
from glob import glob

from gi.repository import Gtk, GLib

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
            self.builder.get_object('frame_setting_gtk_theme').hide()

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

        self.window.hide()

        if have_to_restart:
            md = SkyTempleMessageDialog(self.parent_window,
                                        Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                        Gtk.ButtonsType.OK, _("You need to restart SkyTemple to "
                                                              "apply some of the settings."),
                                        title="SkyTemple")
            md.run()
            md.destroy()

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
