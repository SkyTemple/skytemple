"""Module for handling errors."""
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
import cgitb
import logging
import os
import traceback
import webbrowser
from os.path import expanduser
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Union, Type, Tuple, Any, Optional, Dict

from skytemple_files.common.util import Capturable

try:
    from types import TracebackType
except ImportError:
    TracebackType = Any

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple_files.common.i18n_util import _

logger = logging.getLogger(__name__)
ExceptionInfo = Union[BaseException, Tuple[Type[BaseException], BaseException, TracebackType]]


def show_error_web(exc_info):
    try:
        html = cgitb.html(exc_info)
        with NamedTemporaryFile(delete=False, mode='w', suffix='.html') as tmp_file:
            tmp_file.write(html)
            webbrowser.open_new_tab(Path(tmp_file.name).as_uri())
    except BaseException:
        # Oof. This happens sometimes with some exceptions ("AttributeError: characters_written").
        try:
            html = cgitb.text(exc_info)
            with NamedTemporaryFile(delete=False, mode='w', suffix='.txt') as tmp_file:
                tmp_file.write(html)
                webbrowser.open_new_tab(Path(tmp_file.name).as_uri())
        except BaseException:
            # Hm... now it's getting ridiculous.
            try:
                html = ''.join(traceback.format_exception(*exc_info))
                with NamedTemporaryFile(delete=False, mode='w', suffix='.txt') as tmp_file:
                    tmp_file.write(html)
                    webbrowser.open_new_tab(Path(tmp_file.name).as_uri())
            except BaseException:
                # Yikes!
                md = SkyTempleMessageDialog(None,
                                            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                                            Gtk.ButtonsType.OK,
                                            _("Trying to display the error failed. Wow!"),
                                            title=":(")
                md.run()
                md.destroy()


def display_error(
    exc_info, error_message, error_title=None, window=None, log=True,
    *, context: Optional[Dict[str, Capturable]] = None
):
    if error_title is None:
        error_title = _('SkyTemple - Error!')
    # In case the current working directory is corrupted. Yes, this may happen.
    try:
        os.getcwd()
    except FileNotFoundError:
        os.chdir(expanduser("~"))
    if window is None:
        from skytemple.controller.main import MainController
        window = MainController.window()
    if log:
        logger.error(error_message, exc_info=exc_info)
    if context is None:
        context = {}
    capture_error(exc_info, message=error_message, **context)
    md = SkyTempleMessageDialog(window,
                                Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                                Gtk.ButtonsType.OK,
                                error_message,
                                title=error_title)
    if exc_info is not None:
        button: Gtk.Button = Gtk.Button.new_with_label("Error Details")
        button.connect('clicked', lambda *args: show_error_web(exc_info))
        button_box: Gtk.ButtonBox = Gtk.ButtonBox.new(Gtk.Orientation.VERTICAL)
        button_box.pack_start(button, False, True, 0)
        button_box.set_halign(Gtk.Align.START)
        button_box.show_all()
        md.get_message_area().pack_start(button_box, False, True, 10)
        md.set_position(Gtk.WindowPosition.CENTER)
        md.get_content_area().set_spacing(0)
    md.run()
    md.destroy()


def capture_error(exc_info: Optional[ExceptionInfo], **error_context: Capturable):
    from skytemple.core.settings import SkyTempleSettingsStore
    try:
        settings = SkyTempleSettingsStore()
        if settings.get_allow_sentry():
            from skytemple.core import sentry
            sentry.capture(settings, exc_info, **error_context)
    except Exception as ex:
        logger.error("Failed capturing error", exc_info=ex)
