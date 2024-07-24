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
import logging
import sys
from typing import TYPE_CHECKING, cast
import cairo
from skytemple_files.user_error import mark_as_user_err
from skytemple.core.error_handler import display_error
from skytemple.core.ui_utils import add_dialog_png_filter, data_dir
from skytemple_files.common.util import add_extension_if_missing
from skytemple_files.graphics.chr.model import Chr
from PIL import Image
from gi.repository import Gtk
from skytemple.controller.main import MainController
from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple_files.common.i18n_util import _

from skytemple.init_locale import LocalePatchedGtkTemplate

logger = logging.getLogger(__name__)
if TYPE_CHECKING:
    from skytemple.module.misc_graphics.module import MiscGraphicsModule
import os


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "misc_graphics", "chr.ui"))
class StMiscGraphicsChrPage(Gtk.Paned):
    __gtype_name__ = "StMiscGraphicsChrPage"
    module: MiscGraphicsModule
    item_data: str
    button_import: Gtk.ToolButton = cast(Gtk.ToolButton, Gtk.Template.Child())
    export: Gtk.ToolButton = cast(Gtk.ToolButton, Gtk.Template.Child())
    draw_area: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    chr_palette_variant: Gtk.SpinButton = cast(Gtk.SpinButton, Gtk.Template.Child())
    table_store: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())

    def __init__(self, module: MiscGraphicsModule, item_data: str):
        super().__init__()
        self.module = module
        self.item_data = item_data
        self.chr: Chr = self.module.get_chr(self.item_data)
        self._init_chr()
        self.draw_area.connect("draw", self.exec_draw)

    @Gtk.Template.Callback()
    def on_export_clicked(self, w: Gtk.MenuToolButton):
        dialog = Gtk.FileChooserNative.new(
            _("Export image as PNG..."),
            MainController.window(),
            Gtk.FileChooserAction.SAVE,
            _("_Save"),
            None,
        )
        add_dialog_png_filter(dialog)
        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()
        if response == Gtk.ResponseType.ACCEPT and fn is not None:
            fn = add_extension_if_missing(fn, "png")
            self.chr.to_pil().save(fn)

    @Gtk.Template.Callback()
    def on_button_import_clicked(self, w: Gtk.MenuToolButton):
        dialog = Gtk.FileChooserNative.new(
            _("Import image as indexed PNG..."),
            MainController.window(),
            Gtk.FileChooserAction.OPEN,
            _("_Open"),
            None,
        )
        add_dialog_png_filter(dialog)
        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()
        if response == Gtk.ResponseType.ACCEPT and fn is not None:
            try:
                img = Image.open(fn, "r")
                self.chr.from_pil(img)
            except Exception as err:
                if isinstance(err, AttributeError):
                    mark_as_user_err(err)
                display_error(sys.exc_info(), str(err), _("Error importing chr image."))
            self.module.mark_chr_as_modified(self.item_data)
            self._reinit_image()

    def _init_chr(self):
        self.chr_palette_variant.set_text(str(0))
        self.chr_palette_variant.set_increments(1, 1)
        self.chr_palette_variant.set_range(0, self.chr.get_nb_palettes() - 1)
        self._reinit_image()

    @Gtk.Template.Callback()
    def on_chr_palette_variant_changed(self, widget):
        self._reinit_image()

    def _reinit_image(self):
        variant = int(self.chr_palette_variant.get_text())
        surface = self.chr.to_pil(variant)
        self.surface = pil_to_cairo_surface(surface.convert("RGBA"))
        self.draw_area.queue_draw()

    def exec_draw(self, wdg, ctx: cairo.Context, *args):
        if self.surface:
            wdg.set_size_request(self.surface.get_width(), self.surface.get_height())
            ctx.fill()
            ctx.set_source_surface(self.surface, 0, 0)
            ctx.get_source().set_filter(cairo.Filter.NEAREST)
            ctx.paint()
        return True
