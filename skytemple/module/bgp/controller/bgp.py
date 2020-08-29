#  Copyright 2020 Parakoopa
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
import sys
from typing import TYPE_CHECKING

import cairo

from skytemple.core.error_handler import display_error
from skytemple.core.ui_utils import add_dialog_png_filter

try:
    from PIL import Image
except:
    from pil import Image
from gi.repository import Gtk
from gi.repository.Gtk import ResponseType

from skytemple.controller.main import MainController
from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple.core.module_controller import AbstractController

if TYPE_CHECKING:
    from skytemple.module.bgp.module import BgpModule

logger = logging.getLogger(__name__)


class BgpController(AbstractController):
    def __init__(self, module: 'BgpModule', item_id: int):
        self.module = module
        self.item_id = item_id
        self.bgp = self.module.get_bgp(self.item_id)

        self.builder = None

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'bgp.glade')
        self.builder.connect_signals(self)
        self._reinit_image()
        self.builder.get_object('draw').connect('draw', self.draw)
        return self.builder.get_object('editor_bgp')

    def on_men_bg_export_activate(self, *args):
        dialog: Gtk.Dialog = self.builder.get_object('dialog_bg_export')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        resp = dialog.run()
        dialog.hide()
        if resp == ResponseType.OK:
            dialog = Gtk.FileChooserDialog(
                "Export as PNG...",
                MainController.window(),
                Gtk.FileChooserAction.SAVE,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
            )

            add_dialog_png_filter(dialog)

            response = dialog.run()
            fn = dialog.get_filename()
            if '.' not in fn:
                fn += '.png'
            dialog.destroy()

            if response == Gtk.ResponseType.OK:
                self.bgp.to_pil().save(fn)

    def on_men_bg_import_activate(self, *args):
        dialog: Gtk.Dialog = self.builder.get_object('dialog_bg_import')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        file_chooser: Gtk.FileChooserButton = self.builder.get_object('bg_import_file')

        resp = dialog.run()
        dialog.hide()

        if resp == ResponseType.OK:
            try:
                path = file_chooser.get_filename()
                with open(path, 'rb') as f:
                    self.bgp.from_pil(Image.open(f), True)
            except Exception as err:
                display_error(
                    sys.exc_info(),
                    str(err),
                    "Error importing the image."
                )
            self.module.mark_as_modified(self.item_id)
            self._reinit_image()

    def on_men_tools_tilequant_activate(self, *args):
        MainController.show_tilequant_dialog(16, 16)

    def _reinit_image(self):
        self.surface = pil_to_cairo_surface(self.bgp.to_pil().convert('RGBA'))
        self.builder.get_object('draw').queue_draw()

    def draw(self, wdg, ctx: cairo.Context, *args):
        if self.surface:
            ctx.fill()
            ctx.set_source_surface(self.surface, 0, 0)
            ctx.get_source().set_filter(cairo.Filter.NEAREST)
            ctx.paint()
        return True
