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
import os
import platform
import sys
from skytemple.core.ui_utils import data_dir
from skytemple.core.settings import SkyTempleSettingsStore
from skytemple_files.common.impl_cfg import (
    ENV_SKYTEMPLE_USE_NATIVE,
    change_implementation_type,
)

from skytemple.init_locale import init_locale

settings = SkyTempleSettingsStore()

# Setup Sentry
if settings.get_allow_sentry():
    from skytemple.core import sentry

    sentry.init(settings)

# Setup native library integration
if ENV_SKYTEMPLE_USE_NATIVE not in os.environ:
    change_implementation_type(settings.get_implementation_type())

# Load SSL under Windows and macOS
if getattr(sys, "frozen", False) and platform.system() in ["Windows", "Darwin"]:
    ca_bundle_path = os.path.abspath(
        os.path.join(data_dir(), "..", "certifi", "cacert.pem")
    )
    assert os.path.exists(ca_bundle_path)
    print("Certificates at: ", ca_bundle_path)
    os.environ["SSL_CERT_FILE"] = ca_bundle_path
    os.environ["REQUESTS_CA_BUNDLE"] = ca_bundle_path
    if platform.system() == "Windows":
        import ctypes

        ctypes.cdll.msvcrt._putenv(f"SSL_CERT_FILE={ca_bundle_path}")
        ctypes.cdll.msvcrt._putenv(f"REQUESTS_CA_BUNDLE={ca_bundle_path}")

try:
    init_locale()
except Exception:
    print("Critical failure while trying to init locales.")


import gi
from skytemple_files.common.i18n_util import _

gi.require_version("Gtk", "3.0")

# SKYTEMPLE_LOGLEVEL re-export kept for compatibility until 2.x
from skytemple.core.logger import setup_logging

setup_logging()

from skytemple.core.message_dialog import SkyTempleMessageDialog

# Re-exports kept for compatibility until 2.x

try:
    gi.require_foreign("cairo")
except ImportError:
    from gi.repository import Gtk

    md = SkyTempleMessageDialog(
        None,
        Gtk.DialogFlags.DESTROY_WITH_PARENT,
        Gtk.MessageType.ERROR,
        Gtk.ButtonsType.OK,
        _("PyGObject compiled without Cairo support. Can't start!"),
        title=_("SkyTemple - Error!"),
    )
    md.set_position(Gtk.WindowPosition.CENTER)
    md.run()
    md.destroy()
    exit(1)

from skytemple.app import SkyTempleApplication


def main():
    # TODO: At the moment doesn't support any cli arguments.
    from skytemple.core.async_tasks.delegator import AsyncTaskDelegator

    path = os.path.abspath(os.path.dirname(__file__))
    AsyncTaskDelegator.run_main(SkyTempleApplication(path, settings))


if __name__ == "__main__":
    main()
