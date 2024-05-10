#  Copyright 2020-2024 Capypara and the SkyTemple Contributors
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
import gettext
import locale
import os
import platform
from io import SEEK_SET, BytesIO

from skytemple.core.ui_utils import data_dir

APP = "skytemple"


# Setup locale :(
# TODO: Maybe want to get rid of duplication between SkyTemple and the Randomizer. And clean this up in general...
def init_locale():
    system = platform.system()
    LOCALE_DIR = os.path.abspath(os.path.join(data_dir(), "locale"))
    if hasattr(locale, "bindtextdomain"):
        libintl = locale
        lang, enc = locale.getlocale()
    elif system == "Windows":
        import ctypes
        import ctypes.util

        failed_to_set_locale = False
        if os.getenv("LANG") is None:
            try:
                lang, enc = locale.getlocale()
                os.environ["LANG"] = f"{lang}.{enc}"
                ctypes.cdll.msvcrt._putenv(f"LANG={lang}.{enc}")
                locale.setlocale(locale.LC_ALL, f"{lang}.{enc}")
            except Exception:
                failed_to_set_locale = True

        try:
            locale.getlocale()
        except Exception:
            failed_to_set_locale = True

        if failed_to_set_locale:
            failed_to_set_locale = False

            try:
                lang, enc = locale.getlocale()
                print(
                    f"WARNING: Failed processing current locale {lang}.{enc}. Falling back to {lang}"
                )
                # If this returns None for lang, then we bail!
                if lang is not None:
                    os.environ["LANG"] = lang
                    ctypes.cdll.msvcrt._putenv(f"LANG={lang}")
                    locale.setlocale(locale.LC_ALL, lang)

                    # trying to get locale may fail now, we catch this.
                    locale.getlocale()
                else:
                    failed_to_set_locale = True

                if failed_to_set_locale:
                    print(f"WARNING: Failed to set locale to {lang} falling back to C.")
                    lang = "C"
                    os.environ["LANG"] = "C"
                    ctypes.cdll.msvcrt._putenv("LANG=C")
                    locale.setlocale(locale.LC_ALL, "C")
            except Exception:
                failed_to_set_locale = True
                lang = "C"
                print("final setlocale failed windows")

        libintl_loc = os.path.join(os.path.dirname(__file__), "libintl-8.dll")
        if os.path.exists(libintl_loc):
            libintl = ctypes.cdll.LoadLibrary(libintl_loc)  # type: ignore
        libintl_loc = os.path.join(os.path.dirname(__file__), "intl.dll")
        if os.path.exists(libintl_loc):
            libintl = ctypes.cdll.LoadLibrary(libintl_loc)  # type: ignore
        else:
            try:
                libintl = ctypes.cdll.LoadLibrary(ctypes.util.find_library("libintl-8"))  # type: ignore
            except Exception:
                libintl = ctypes.cdll.LoadLibrary(ctypes.util.find_library("intl"))  # type: ignore
    elif system == "Darwin":
        import ctypes

        # TODO: Move to skytemple-files
        from Foundation import NSLocale  # type: ignore

        lang = NSLocale.preferredLanguages()[0].replace("-", "_")  # type: ignore
        locale.setlocale(locale.LC_ALL, lang)
        print(f"LANG={lang}")
        os.environ["LANG"] = lang  # type: ignore
        libintl = ctypes.cdll.LoadLibrary("libintl.8.dylib")  # type: ignore
    libintl.bindtextdomain(APP, LOCALE_DIR)  # type: ignore
    try:
        libintl.bind_textdomain_codeset(APP, "UTF-8")  # type: ignore
    except Exception:
        pass
    try:
        libintl.libintl_setlocale(0, lang)  # type: ignore
    except Exception:
        pass
    libintl.textdomain(APP)
    gettext.bindtextdomain(APP, LOCALE_DIR)
    gettext.textdomain(APP)
    try:
        if "LC_ALL" not in os.environ or os.environ["LC_ALL"] != "C":
            if "LC_ALL" not in os.environ:
                loc = locale.getlocale()[0]  # type: ignore
            else:
                loc = os.environ["LC_ALL"]
            from skytemple_files.common.i18n_util import reload_locale

            base_loc = loc.split("_")[0]  # type: ignore
            fallback_loc = base_loc
            for subdir in next(os.walk(LOCALE_DIR))[1]:
                if subdir.startswith(base_loc):
                    fallback_loc = subdir
                    break
            reload_locale(
                APP,
                localedir=LOCALE_DIR,
                main_languages=list({loc, base_loc, fallback_loc}),  # type: ignore
            )
    except Exception as ex:
        print("Failed setting up Python locale.")
        print(ex)


# Hot-patch GtkTemplate decorator under MacOS and Windows to load strings from the locale
#
# Yes, this is absolutely awful, but even with our best efforts, the code above just doesn't
# reliably work.
class LocalePatchedGtkTemplate:
    def __init__(self, filename: str) -> None:
        from gi.repository import Gtk
        from skytemple_files.common.i18n_util import _
        from xml.etree import ElementTree

        system = platform.system()
        if system == "Windows" or system == "Darwin":
            tree = ElementTree.parse(filename)
            for node in tree.iter():
                if "translatable" in node.attrib and node.text is not None:
                    node.text = _(node.text)
            content = BytesIO()
            tree.write(content, encoding="utf-8", xml_declaration=True)
            content.seek(0, SEEK_SET)
            self._impl = Gtk.Template(string=str(content.read(), "utf-8"))
        else:
            self._impl = Gtk.Template(filename=filename)

    def __call__(self, cls):
        return self._impl.__call__(cls)
