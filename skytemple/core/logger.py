"""Logging configuration."""
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
import traceback
from logging.handlers import RotatingFileHandler

from gi.repository import GLib

from skytemple.core.error_handler import display_error
from skytemple_files.common.project_file_manager import ProjectFileManager
from skytemple_files.common.i18n_util import _, f

logger = logging.getLogger('system')


def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    try:
        # noinspection PyUnusedLocal
        traceback_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        GLib.idle_add(lambda: display_error(
            (exc_type, exc_value, exc_traceback),
             f(_("An uncaught exception occurred! This shouldn't happen, please report it!")) + "\n\n" + traceback_str,
            _("SkyTemple - Uncaught error!"), log=False
        ))
    except:
        pass


def setup_logging():
    """
    Creates a rotating log
    """

    sys.excepthook = handle_exception

    dirn = ProjectFileManager.shared_config_dir()
    os.makedirs(dirn, exist_ok=True)
    handler = RotatingFileHandler(
        os.path.join(dirn, 'skytemple.log'),
        maxBytes=100000, backupCount=5)
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(), handler]
    )
