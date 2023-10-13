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
import os
from typing import cast

from gi.repository import Gtk
from skytemple_files.common.i18n_util import _

from skytemple.core import sentry_ext
from skytemple.core.ui_utils import data_dir

EMAIL_TO_USE = "_reporter@skytemple.org"


@Gtk.Template(filename=os.path.join(data_dir(), "widget", "user_feedback.ui"))
class StUserFeedbackWindow(Gtk.Window):
    """
    A window that asks the user for feedback on an error that just happened and sends this to Sentry.
    """

    __gtype_name__ = "StUserFeedbackWindow"

    button_send = cast(Gtk.Button, Gtk.Template.Child())
    button_cancel = cast(Gtk.Button, Gtk.Template.Child())
    entry_name = cast(Gtk.Entry, Gtk.Template.Child())
    textview_comments = cast(Gtk.TextView, Gtk.Template.Child())

    sentry_event_id: str

    def __init__(self, sentry_event_id: str, parent: Gtk.Window):
        super().__init__(
            transient_for=parent,
            parent=parent,
            attached_to=parent,
            destroy_with_parent=True,
            modal=True,
            title=_("Report Error"),
        )
        self.sentry_event_id = sentry_event_id

    @Gtk.Template.Callback()
    def on_button_send_clicked(self, *args):
        name = self.entry_name.get_text().strip()
        if name == "":
            name = "Anonymous"
        comments_buffer = self.textview_comments.get_buffer()
        comments = (
            self.textview_comments.get_buffer()
            .get_text(
                comments_buffer.get_start_iter(),
                comments_buffer.get_end_iter(),
                False,
            )
            .strip()
        )
        sentry_ext.capture_user_feedback(
            {
                "event_id": self.sentry_event_id,
                "name": name,
                "email": EMAIL_TO_USE,
                "comments": comments,
            }
        )
        self.close()

    @Gtk.Template.Callback()
    def on_button_cancel_clicked(self, *args):
        self.close()
