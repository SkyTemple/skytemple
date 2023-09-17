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
import locale
import gettext
from skytemple.core.ui_utils import data_dir, APP, builder_get_assert
from skytemple.core.settings import SkyTempleSettingsStore
from skytemple_files.common.impl_cfg import ENV_SKYTEMPLE_USE_NATIVE, change_implementation_type

settings = SkyTempleSettingsStore()

# Setup Sentry
if settings.get_allow_sentry():
    from skytemple.core import sentry
    sentry.init()

# Setup native library integration
if ENV_SKYTEMPLE_USE_NATIVE not in os.environ:
    change_implementation_type(settings.get_implementation_type())

# Setup locale :(
LOCALE_DIR = os.path.abspath(os.path.join(data_dir(), 'locale'))
if hasattr(locale, 'bindtextdomain'):
    libintl = locale
elif sys.platform.startswith('win'):
    import ctypes
    import ctypes.util
    failed_to_set_locale = False
    if os.getenv('LANG') is None:
        lang, enc = locale.getdefaultlocale()
        os.environ['LANG'] = f"{lang}.{enc}"
        ctypes.cdll.msvcrt._putenv(f"LANG={lang}.{enc}")
        try:
            locale.setlocale(locale.LC_ALL, f"{lang}.{enc}")
        except:
            failed_to_set_locale = True

    try:
        locale.getlocale()
    except:
        failed_to_set_locale = True

    if failed_to_set_locale:
        failed_to_set_locale = False

        lang, env = locale.getdefaultlocale()
        print(f"WARNING: Failed processing current locale {lang}.{env}. Falling back to {lang}")
        os.environ['LANG'] = lang
        ctypes.cdll.msvcrt._putenv(f"LANG={lang}")
        try:
            locale.setlocale(locale.LC_ALL, lang)
        except:
            failed_to_set_locale = True

        try:
            locale.getlocale()
        except:
            failed_to_set_locale = True

        if failed_to_set_locale:
            print(f"WARNING: Failed to set locale to {lang} falling back to C.")
            os.environ['LANG'] = "C"
            ctypes.cdll.msvcrt._putenv("LANG=C")
            locale.setlocale(locale.LC_ALL, "C")

    libintl_loc = os.path.join(os.path.dirname(__file__), 'libintl-8.dll')
    if os.path.exists(libintl_loc):
        libintl = ctypes.cdll.LoadLibrary(libintl_loc)
    libintl_loc = os.path.join(os.path.dirname(__file__), 'intl.dll')
    if os.path.exists(libintl_loc):
        libintl = ctypes.cdll.LoadLibrary(libintl_loc)
    else:
        try:
            libintl = ctypes.cdll.LoadLibrary(ctypes.util.find_library('libintl-8'))
        except:
            libintl = ctypes.cdll.LoadLibrary(ctypes.util.find_library('intl'))
elif sys.platform == 'darwin':
    import ctypes
    libintl = ctypes.cdll.LoadLibrary('libintl.dylib')
if not os.getenv('LC_ALL'):
    try:
        os.environ['LC_ALL'] = settings.get_locale()
        locale.setlocale(locale.LC_ALL, settings.get_locale())
    except locale.Error as ex:
        logging.error("Failed setting locale", exc_info=ex)
libintl.bindtextdomain(APP, LOCALE_DIR)  # type: ignore
try:
    libintl.bind_textdomain_codeset(APP, 'UTF-8')  # type: ignore
    libintl.libintl_setlocale(0, settings.get_locale())  # type: ignore
except:
    pass
gettext.bindtextdomain(APP, LOCALE_DIR)
gettext.textdomain(APP)
try:
    if os.environ['LC_ALL'] != 'C':
        loc = os.environ['LC_ALL']
        if loc == '':
            loc = locale.getdefaultlocale()[0]  # type: ignore
        from skytemple_files.common.i18n_util import reload_locale
        base_loc = loc.split('_')[0]
        fallback_loc = base_loc
        for subdir in next(os.walk(LOCALE_DIR))[1]:
            if subdir.startswith(base_loc):
                fallback_loc = subdir
                break
        reload_locale(APP, localedir=LOCALE_DIR, main_languages=list({loc, base_loc, fallback_loc}))
except Exception as ex:
    print("Failed setting up Python locale.")
    print(ex)
from skytemple.core import ui_utils
from importlib import reload
reload(ui_utils)


if getattr(sys, 'frozen', False):
    # Running via PyInstaller. Fix SSL configuration
    os.environ["SSL_CERT_FILE"] = os.path.join(
        os.path.dirname(sys.executable), "certifi", "cacert.pem"
    )


import gi
from skytemple_files.common.i18n_util import _

gi.require_version('Gtk', '3.0')

from skytemple.core.logger import setup_logging, SKYTEMPLE_LOGLEVEL

setup_logging()

from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.events.manager import EventManager
from skytemple.core.modules import Modules
from skytemple_icons import icons
from skytemple_ssb_debugger.main import get_debugger_data_dir
from skytemple.core.ui_utils import make_builder

try:
    gi.require_foreign("cairo")
except ImportError:
    from gi.repository import Gtk

    md = SkyTempleMessageDialog(None,
                                Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                                Gtk.ButtonsType.OK, _("PyGObject compiled without Cairo support. Can't start!"),
                                title=_("SkyTemple - Error!"))
    md.set_position(Gtk.WindowPosition.CENTER)
    md.run()
    md.destroy()
    exit(1)

from gi.repository import Gtk, Gdk, GLib
from gi.repository.Gtk import Window
from skytemple.controller.main import MainController


def run_main(settings: SkyTempleSettingsStore):
    # TODO: Gtk.Application: https://python-gtk-3-tutorial.readthedocs.io/en/latest/application.html
    path = os.path.abspath(os.path.dirname(__file__))

    if sys.platform.startswith('win'):
        # Load theming under Windows
        _load_theme(settings)
        # Solve issue #12
        try:
            from skytemple_files.common.platform_utils.win import win_set_error_mode
            win_set_error_mode()
        except BaseException:
            # This really shouldn't fail, but it's not important enough to crash over
            pass

    if sys.platform.startswith('darwin'):
        # Load theming under macOS
        _load_theme(settings)

        # The search path is wrong if SkyTemple is executed as an .app bundle
        if getattr(sys, 'frozen', False):
            path = os.path.dirname(sys.executable)

    itheme: Gtk.IconTheme = Gtk.IconTheme.get_default()
    itheme.append_search_path(os.path.abspath(icons()))
    itheme.append_search_path(os.path.abspath(os.path.join(data_dir(), "icons")))
    itheme.append_search_path(os.path.abspath(os.path.join(get_debugger_data_dir(), "icons")))
    itheme.rescan_if_needed()

    # Load Builder and Window
    builder = make_builder(os.path.join(path, "skytemple.glade"))
    main_window = builder_get_assert(builder, Window, "main_window")
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
    default_screen = Gdk.Screen.get_default()
    if default_screen is not None:
        Gtk.StyleContext.add_provider_for_screen(
            default_screen, style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    # Init. core events
    event_manager = EventManager.instance()
    if settings.get_integration_discord_enabled():
        try:
            from skytemple.core.events.impl.discord import DiscordPresence
            discord_listener = DiscordPresence()
            event_manager.register_listener(discord_listener)
        except BaseException as exc:
            logging.warning("Error setting up Discord integration:", exc_info=exc)

    # Load modules
    Modules.load(settings)

    # Load main window + controller
    MainController(builder, main_window, settings)

    main_window.present()
    main_window.set_icon_name('skytemple')


def _load_theme(settings: SkyTempleSettingsStore):
    gtk_settings = Gtk.Settings.get_default()
    if gtk_settings is not None:
        gtk_settings.set_property("gtk-theme-name", settings.get_gtk_theme(default='Arc-Dark'))


def main():
    # TODO: At the moment doesn't support any cli arguments.
    from skytemple.core.async_tasks.delegator import AsyncTaskDelegator
    AsyncTaskDelegator.run_main(run_main, settings)


if __name__ == '__main__':
    main()
