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
from typing import TYPE_CHECKING

from gi.repository.Gtk import Widget, TextBuffer, Entry

from skytemple.core.module_controller import AbstractController
if TYPE_CHECKING:
    from skytemple.module.rom.module import RomModule

class MainController(AbstractController):
    def __init__(self, module: 'RomModule', item_id: int):
        self.module = module
        self.project = module.project
        self.icon_banner = module.project.get_icon_banner()

    def get_view(self) -> Widget:
        self.builder = self._get_builder(__file__, 'rom.glade')

        file_name = os.path.basename(self.module.project.filename)
        self.builder.get_object('file_name').set_text(file_name)

        self.builder.get_object('name').set_text(self.project.get_rom_name())
        self.builder.get_object('id_code').set_text(self.project.get_id_code())

        title_japanese_buffer = self.builder.get_object('title_japanese').get_buffer()
        title_japanese_buffer.set_text(self.icon_banner.title_japanese)
        title_japanese_buffer.connect('changed', self.on_title_japanese_changed)

        title_english_buffer = self.builder.get_object('title_english').get_buffer()
        title_english_buffer.set_text(self.icon_banner.title_english)
        title_english_buffer.connect('changed', self.on_title_english_changed)

        title_french_buffer = self.builder.get_object('title_french').get_buffer()
        title_french_buffer.set_text(self.icon_banner.title_french)
        title_french_buffer.connect('changed', self.on_title_french_changed)

        title_german_buffer = self.builder.get_object('title_german').get_buffer()
        title_german_buffer.set_text(self.icon_banner.title_german)
        title_german_buffer.connect('changed', self.on_title_german_changed)

        title_italian_buffer = self.builder.get_object('title_italian').get_buffer()
        title_italian_buffer.set_text(self.icon_banner.title_italian)
        title_italian_buffer.connect('changed', self.on_title_italian_changed)

        title_spanish_buffer = self.builder.get_object('title_spanish').get_buffer()
        title_spanish_buffer.set_text(self.icon_banner.title_spanish)
        title_spanish_buffer.connect('changed', self.on_title_spanish_changed)

        self.builder.connect_signals(self)

        return self.builder.get_object('box_list')

    def on_title_japanese_changed(self, buffer: TextBuffer):
        (start, end) = buffer.get_bounds()
        self.icon_banner.title_japanese = buffer.get_text(start, end, True)
        self.module.mark_as_modified()

    def on_title_english_changed(self, buffer: TextBuffer):
        (start, end) = buffer.get_bounds()
        self.icon_banner.title_english = buffer.get_text(start, end, True)
        self.module.mark_as_modified()

    def on_title_french_changed(self, buffer: TextBuffer):
        (start, end) = buffer.get_bounds()
        self.icon_banner.title_french = buffer.get_text(start, end, True)
        self.module.mark_as_modified()

    def on_title_german_changed(self, buffer: TextBuffer):
        (start, end) = buffer.get_bounds()
        self.icon_banner.title_german = buffer.get_text(start, end, True)
        self.module.mark_as_modified()

    def on_title_italian_changed(self, buffer: TextBuffer):
        (start, end) = buffer.get_bounds()
        self.icon_banner.title_italian = buffer.get_text(start, end, True)
        self.module.mark_as_modified()

    def on_title_spanish_changed(self, buffer: TextBuffer):
        (start, end) = buffer.get_bounds()
        self.icon_banner.title_spanish = buffer.get_text(start, end, True)
        self.module.mark_as_modified()

    def on_name_changed(self, entry: Entry):
        try:
            self.project.set_rom_name(entry.get_text())
            self.module.mark_as_modified()
        except:
            # Invalid input, e.g. non-ASCII characters
            entry.set_text(self.project.get_rom_name())

    def on_id_code_changed(self, entry: Entry):
        try:
            self.project.set_id_code(entry.get_text())
            self.module.mark_as_modified()
        except:
            # Invalid input, e.g. non-ASCII characters
            entry.set_text(self.project.get_id_code())
