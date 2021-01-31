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
import logging
import os
import sys
from typing import TYPE_CHECKING, Optional, Dict

import cairo

from skytemple.core.error_handler import display_error
from skytemple.core.ui_utils import add_dialog_png_filter
from skytemple_files.graphics.chr.model import Chr

try:
    from PIL import Image
except:
    from pil import Image
from gi.repository import Gtk
from gi.repository.Gtk import ResponseType

from skytemple.controller.main import MainController
from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple.core.module_controller import AbstractController
from skytemple_files.common.i18n_util import f, _

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from skytemple.module.misc_graphics.module import MiscGraphicsModule


class ChrController(AbstractController):
    def __init__(self, module: 'MiscGraphicsModule', filename: str):
        self.module = module
        self.filename = filename
        self.chr: Chr = self.module.get_chr(self.filename)
        
        self.builder = None

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'chr.glade')

        self._init_chr()
        
        self.builder.connect_signals(self)
        self.builder.get_object('draw').connect('draw', self.draw)
        return self.builder.get_object('editor')

    def on_export_clicked(self, w: Gtk.MenuToolButton):
        dialog = Gtk.FileChooserNative.new(
            _("Export image as PNG..."),
            MainController.window(),
            Gtk.FileChooserAction.SAVE,
            _("_Save"), None
        )

        add_dialog_png_filter(dialog)

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            if '.' not in fn:
                fn += '.png'
            self.chr.to_pil().save(fn)

    def on_import_clicked(self, w: Gtk.MenuToolButton):
        dialog = Gtk.FileChooserNative.new(
            _("Import image as indexed PNG..."),
            MainController.window(),
            Gtk.FileChooserAction.OPEN,
            _("_Open"), None
        )

        add_dialog_png_filter(dialog)

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            try:
                img = Image.open(fn, 'r')
                self.chr.from_pil(img)
            except Exception as err:
                display_error(
                    sys.exc_info(),
                    str(err),
                    _("Error importing chr image.")
                )
            self.module.mark_chr_as_modified(self.filename)
            self._reinit_image()
        
    def _init_chr(self):
        self.builder.get_object('chr_palette_variant').set_text(str(0))
        self.builder.get_object('chr_palette_variant').set_increments(1,1)
        self.builder.get_object('chr_palette_variant').set_range(0, self.chr.get_nb_palettes()-1)
        self._reinit_image()

    def on_chr_palette_variant_changed(self, widget):
        self._reinit_image()
    
    def _reinit_image(self):
        variant = int(self.builder.get_object('chr_palette_variant').get_text())
        surface = self.chr.to_pil(variant)
        self.surface = pil_to_cairo_surface(surface.convert('RGBA'))
        self.builder.get_object('draw').queue_draw()
    
    def draw(self, wdg, ctx: cairo.Context, *args):
        if self.surface:
            wdg.set_size_request(self.surface.get_width(), self.surface.get_height())
            ctx.fill()
            ctx.set_source_surface(self.surface, 0, 0)
            ctx.get_source().set_filter(cairo.Filter.NEAREST)
            ctx.paint()
        return True
