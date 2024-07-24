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
import os
import sys
from typing import TYPE_CHECKING, cast
import cairo
from PIL import Image
from gi.repository import Gtk
from skytemple.core.error_handler import display_error
from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple.core.ui_utils import add_dialog_png_filter, data_dir
from skytemple_files.common.i18n_util import _
from skytemple.controller.main import MainController as SkyTempleMainController
from skytemple_files.common.util import add_extension_if_missing

from skytemple.init_locale import LocalePatchedGtkTemplate

if TYPE_CHECKING:
    from skytemple.module.rom.module import RomModule


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "rom", "main.ui"))
class StRomMainPage(Gtk.Box):
    __gtype_name__ = "StRomMainPage"
    module: RomModule
    item_data: int
    file_name: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    draw_icon: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    export_icon: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    import_icon: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    name: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    id_code: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    title_japanese: Gtk.TextView = cast(Gtk.TextView, Gtk.Template.Child())
    title_spanish: Gtk.TextView = cast(Gtk.TextView, Gtk.Template.Child())
    title_italian: Gtk.TextView = cast(Gtk.TextView, Gtk.Template.Child())
    title_german: Gtk.TextView = cast(Gtk.TextView, Gtk.Template.Child())
    title_french: Gtk.TextView = cast(Gtk.TextView, Gtk.Template.Child())
    title_english: Gtk.TextView = cast(Gtk.TextView, Gtk.Template.Child())

    def __init__(self, module: RomModule, item_data: int):
        super().__init__()
        self.module = module
        self.item_data = item_data

        self.loading = True
        self.project = module.project
        self.icon_banner = module.project.get_icon_banner()
        file_name = os.path.basename(self.module.project.filename)
        self.file_name.set_text(file_name)
        self.name.set_text(self.project.get_rom_name())
        self.id_code.set_text(self.project.get_id_code())
        self.icon_surface = pil_to_cairo_surface(self.icon_banner.icon.to_pil().convert("RGBA"))
        title_japanese_buffer = self.title_japanese.get_buffer()
        title_japanese_buffer.set_text(self.icon_banner.title_japanese)
        title_japanese_buffer.connect("changed", self.on_title_japanese_changed)
        title_english_buffer = self.title_english.get_buffer()
        title_english_buffer.set_text(self.icon_banner.title_english)
        title_english_buffer.connect("changed", self.on_title_english_changed)
        title_french_buffer = self.title_french.get_buffer()
        title_french_buffer.set_text(self.icon_banner.title_french)
        title_french_buffer.connect("changed", self.on_title_french_changed)
        title_german_buffer = self.title_german.get_buffer()
        title_german_buffer.set_text(self.icon_banner.title_german)
        title_german_buffer.connect("changed", self.on_title_german_changed)
        title_italian_buffer = self.title_italian.get_buffer()
        title_italian_buffer.set_text(self.icon_banner.title_italian)
        title_italian_buffer.connect("changed", self.on_title_italian_changed)
        title_spanish_buffer = self.title_spanish.get_buffer()
        title_spanish_buffer.set_text(self.icon_banner.title_spanish)
        title_spanish_buffer.connect("changed", self.on_title_spanish_changed)
        self.loading = False

    @Gtk.Template.Callback()
    def on_draw_icon_draw(self, widget: Gtk.DrawingArea, ctx: cairo.Context):
        scale = 2
        ctx.scale(scale, scale)
        ctx.set_source_surface(self.icon_surface)
        ctx.get_source().set_filter(cairo.Filter.NEAREST)
        ctx.paint()
        ctx.scale(1 / scale, 1 / scale)
        return True

    @Gtk.Template.Callback()
    def on_export_icon_clicked(self, *args):
        dialog = Gtk.FileChooserNative.new(
            _("Export game icon as PNG..."),
            SkyTempleMainController.window(),
            Gtk.FileChooserAction.SAVE,
            None,
            None,
        )
        add_dialog_png_filter(dialog)
        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()
        if response == Gtk.ResponseType.ACCEPT and fn is not None:
            fn = add_extension_if_missing(fn, "png")
            self.icon_banner.icon.to_pil().save(fn)

    @Gtk.Template.Callback()
    def on_import_icon_clicked(self, *args):
        dialog = Gtk.FileChooserNative.new(
            _("Import game icon from PNG..."),
            SkyTempleMainController.window(),
            Gtk.FileChooserAction.OPEN,
            None,
            None,
        )
        add_dialog_png_filter(dialog)
        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()
        if response == Gtk.ResponseType.ACCEPT and fn is not None:
            try:
                self.icon_banner.icon.from_pil(Image.open(fn))
            except Exception as err:
                display_error(
                    sys.exc_info(),
                    _("Failed importing game icon:\n") + str(err),
                    _("Could not import."),
                )
            self.icon_surface = pil_to_cairo_surface(self.icon_banner.icon.to_pil().convert("RGBA"))
            self.draw_icon.queue_draw()
            # Mark as modified
            self.module.mark_as_modified()

    def on_title_japanese_changed(self, buffer: Gtk.TextBuffer):
        start, end = buffer.get_bounds()
        self.icon_banner.title_japanese = buffer.get_text(start, end, True)
        self.module.mark_as_modified()

    def on_title_english_changed(self, buffer: Gtk.TextBuffer):
        start, end = buffer.get_bounds()
        self.icon_banner.title_english = buffer.get_text(start, end, True)
        self.module.mark_as_modified()

    def on_title_french_changed(self, buffer: Gtk.TextBuffer):
        start, end = buffer.get_bounds()
        self.icon_banner.title_french = buffer.get_text(start, end, True)
        self.module.mark_as_modified()

    def on_title_german_changed(self, buffer: Gtk.TextBuffer):
        start, end = buffer.get_bounds()
        self.icon_banner.title_german = buffer.get_text(start, end, True)
        self.module.mark_as_modified()

    def on_title_italian_changed(self, buffer: Gtk.TextBuffer):
        start, end = buffer.get_bounds()
        self.icon_banner.title_italian = buffer.get_text(start, end, True)
        self.module.mark_as_modified()

    def on_title_spanish_changed(self, buffer: Gtk.TextBuffer):
        start, end = buffer.get_bounds()
        self.icon_banner.title_spanish = buffer.get_text(start, end, True)
        self.module.mark_as_modified()

    @Gtk.Template.Callback()
    def on_name_changed(self, entry: Gtk.Entry):
        if self.loading:
            return
        try:
            self.project.set_rom_name(entry.get_text())
            self.module.mark_as_modified()
        except Exception:
            # Invalid input, e.g. non-ASCII characters
            entry.set_text(self.project.get_rom_name())

    @Gtk.Template.Callback()
    def on_id_code_changed(self, entry: Gtk.Entry):
        if self.loading:
            return
        try:
            self.project.set_id_code(entry.get_text())
            self.module.mark_as_modified()
        except Exception:
            # Invalid input, e.g. non-ASCII characters
            entry.set_text(self.project.get_id_code())
