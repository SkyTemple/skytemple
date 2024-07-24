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
from __future__ import annotations
import os.path
import webbrowser
from typing import TYPE_CHECKING, cast
from gi.repository import Gtk, Gdk, GLib
from skytemple.controller.main import MainController
from skytemple.core.ui_utils import data_dir, assert_not_none
from skytemple.init_locale import LocalePatchedGtkTemplate

if TYPE_CHECKING:
    from skytemple.module.patch.module import PatchModule
import os


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "patch", "cot.ui"))
class StPatchCotPage(Gtk.Box):
    __gtype_name__ = "StPatchCotPage"
    module: PatchModule
    item_data: None
    box_normal: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    tutorial_video: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    img_tutorial: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    readme_cot: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    img: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    readme_rod: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    image1: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())

    def __init__(self, module: PatchModule, item_data: None):
        super().__init__()
        self.module = module
        self.item_data = item_data
        img_tutorial = self.img_tutorial
        img_tutorial.set_from_file(os.path.join(data_dir(), "thumb_cot.png"))

    @Gtk.Template.Callback()
    def on_tutorial_video_enter(self, *args):
        img_btn = self.tutorial_video
        pointer = Gdk.Cursor.new_from_name(MainController.window().get_display(), "pointer")
        GLib.idle_add(lambda: assert_not_none(img_btn.get_window()).set_cursor(pointer))

    @Gtk.Template.Callback()
    def on_tutorial_video_leave(self, *args):
        img_btn = self.tutorial_video
        default = Gdk.Cursor.new_from_name(MainController.window().get_display(), "default")
        GLib.idle_add(lambda: assert_not_none(img_btn.get_window()).set_cursor(default))

    @Gtk.Template.Callback()
    def on_tutorial_video_clicked(self, *args):
        webbrowser.open_new_tab("https://skytemple.org/cot_tutorial")

    @Gtk.Template.Callback()
    def on_readme_cot_clicked(self, *args):
        webbrowser.open_new_tab("https://github.com/SkyTemple/c-of-time/blob/main/README.md")

    @Gtk.Template.Callback()
    def on_readme_rod_clicked(self, *args):
        webbrowser.open_new_tab("https://github.com/SkyTemple/c-of-time/blob/main/rust/README.md")
