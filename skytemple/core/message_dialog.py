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
import os

from gi.repository import Gtk

from skytemple.core.ui_utils import data_dir

IMG_HAPPY = 'duskako_happy.png'
IMG_SAD = 'duskako_sad.png'
IMG_NEUTRAL = 'duskako_neutral.png'

IMGS = {
    Gtk.MessageType.INFO: IMG_NEUTRAL,
    Gtk.MessageType.ERROR: IMG_SAD,
    Gtk.MessageType.WARNING: IMG_NEUTRAL,
    Gtk.MessageType.QUESTION: IMG_NEUTRAL,
    Gtk.MessageType.OTHER: IMG_NEUTRAL,
}
IS_SUCCESS = 'is_success'


class SkyTempleMessageDialog(Gtk.MessageDialog):
    def __init__(
            self, parent: Gtk.Window, dialog_flags: Gtk.DialogFlags,
            message_type: Gtk.MessageType, buttons_type: Gtk.ButtonsType,
            *args, **kwargs
    ):
        img = IMGS[message_type]
        if IS_SUCCESS in kwargs:
            if kwargs[IS_SUCCESS]:
                img = IMG_HAPPY
            del kwargs[IS_SUCCESS]
        self.img: Gtk.Image = Gtk.Image.new_from_file(os.path.join(data_dir(), img))
        super().__init__(parent, dialog_flags, message_type, buttons_type, *args, **kwargs)

        box: Gtk.Box = self.get_message_area()
        parent: Gtk.Box = box.get_parent()
        box.set_valign(Gtk.Align.CENTER)

        parent.pack_start(self.img, False, False, 0)
        parent.pack_start(box, False, False, 0)

        parent.child_set_property(self.img, 'position', 0)
        self.img.show()
