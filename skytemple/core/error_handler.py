"""Module for handling errors."""
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
import cgitb
import logging
import os
import traceback
import webbrowser
from os.path import expanduser
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Union, Type, Tuple, Any, Optional, Dict, cast

from skytemple_files.common.util import Capturable
from skytemple_files.user_error import USER_ERROR_MARK

try:
    from types import TracebackType
except ImportError:
    TracebackType = Any  # type: ignore

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple_files.common.i18n_util import _

logger = logging.getLogger(__name__)
ExceptionInfo = Union[BaseException, Tuple[Type[BaseException], BaseException, TracebackType]]


def show_error_web(exc_info):
    tmp_file1 = None
    tmp_file2 = None
    tmp_file3 = None
    try:
        html = cgitb.html(exc_info)
        with NamedTemporaryFile(delete=False, mode='w', suffix='.html') as tmp_file1:
            tmp_file1.write(html)
            webbrowser.open_new_tab(Path(tmp_file1.name).as_uri())
    except BaseException:
        # Oof. This happens sometimes with some exceptions ("AttributeError: characters_written").
        try:
            html = cgitb.text(exc_info)
            with NamedTemporaryFile(delete=False, mode='w', suffix='.txt') as tmp_file2:
                tmp_file2.write(html)
                webbrowser.open_new_tab(Path(tmp_file2.name).as_uri())
        except BaseException:
            # Hm... now it's getting ridiculous.
            try:
                html = ''.join(traceback.format_exception(*exc_info))
                with NamedTemporaryFile(delete=False, mode='w', suffix='.txt') as tmp_file3:
                    tmp_file3.write(html)
                    webbrowser.open_new_tab(Path(tmp_file3.name).as_uri())
            except BaseException:
                # Yikes!
                md = SkyTempleMessageDialog(None,
                                            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                                            Gtk.ButtonsType.OK,
                                            (
                                                _("Trying to display the error failed. Wow!")
                                                + "\n"
                                                + _("You can try opening one of the following file manually in a web browser or text editor: ")
                                                + "\n - " + (tmp_file1.name if tmp_file1 is not None else "")
                                                + "\n - " + (tmp_file2.name if tmp_file2 is not None else "")
                                                + "\n - " + (tmp_file3.name if tmp_file3 is not None else "")
                                            ),

                                            title=":(", text_selectable=True)
                md.run()
                md.destroy()


def display_error(
    exc_info, error_message, error_title=None, window=None, log=True,
    *, context: Optional[Dict[str, Capturable]] = None, should_report=True
):
    """
    :param should_report: Whether or not the error should be reported. UserValueErrors are never to be reported.
    """
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
    if should_report and should_be_reported(exc_info):
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
        cast(Gtk.Box, md.get_message_area()).pack_start(button_box, False, True, 10)
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


def should_be_reported(exc_info: Optional[ExceptionInfo]):
    if exc_info is None:
        return True
    if isinstance(exc_info, tuple):
        exc = exc_info[1]
    else:
        exc = exc_info

    return not hasattr(exc, USER_ERROR_MARK)
