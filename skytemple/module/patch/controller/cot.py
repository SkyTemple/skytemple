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
import os.path
import webbrowser
from typing import TYPE_CHECKING

from gi.repository import Gtk, Gdk, GLib

from skytemple.controller.main import MainController
from skytemple.core.module_controller import SimpleController, AbstractController
from skytemple_files.common.i18n_util import _

from skytemple.core.ui_utils import data_dir, builder_get_assert, assert_not_none

if TYPE_CHECKING:
    from skytemple.module.patch.module import PatchModule


class CotController(AbstractController):
    def __init__(self, module: 'PatchModule', *args):
        self.module = module

        self.builder: Gtk.Builder = None  # type: ignore

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'cot.glade')
        assert self.builder

        img_tutorial = builder_get_assert(self.builder, Gtk.Image, 'img_tutorial')
        img_tutorial.set_from_file(os.path.join(data_dir(), 'thumb_cot.png'))

        self.builder.connect_signals(self)
        return builder_get_assert(self.builder, Gtk.Widget, 'main_box')

    def on_tutorial_video_enter(self, *args):
        img_btn = builder_get_assert(self.builder, Gtk.Button, 'tutorial_video')
        pointer = Gdk.Cursor.new_from_name(MainController.window().get_display(), 'pointer')
        GLib.idle_add(lambda: assert_not_none(img_btn.get_window()).set_cursor(pointer))

    def on_tutorial_video_leave(self, *args):
        img_btn = builder_get_assert(self.builder, Gtk.Button, 'tutorial_video')
        default = Gdk.Cursor.new_from_name(MainController.window().get_display(), 'default')
        GLib.idle_add(lambda: assert_not_none(img_btn.get_window()).set_cursor(default))

    def on_tutorial_video_clicked(self, *args):
        webbrowser.open_new_tab('https://skytemple.org/cot_tutorial')

    def on_readme_cot_clicked(self, *args):
        webbrowser.open_new_tab('https://github.com/SkyTemple/c-of-time/blob/main/README.md')

    def on_readme_rod_clicked(self, *args):
        webbrowser.open_new_tab('https://github.com/SkyTemple/c-of-time/blob/main/rust/README.md')
