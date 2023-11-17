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
from __future__ import annotations
import os
import webbrowser
from typing import TYPE_CHECKING

from gi.repository import Gtk

from skytemple.core.ui_utils import data_dir

if TYPE_CHECKING:
    from skytemple.module.music.module import MusicModule


@Gtk.Template(filename=os.path.join(data_dir(), "widget", "music", "main.ui"))
class StMusicMainPage(Gtk.Box):
    __gtype_name__ = "StMusicMainPage"

    module: MusicModule
    item_data: None

    def __init__(self, module: MusicModule, item_data):
        super().__init__()

        self.module = module
        self.item_data = item_data

    @Gtk.Template.Callback()
    def on_button_sky_song_builder_clicked(self, *args):
        webbrowser.open_new_tab(
            "https://wiki.skytemple.org/index.php?title=SkyTemple:UI-Link/skytemple--music--main"
        )
