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
from skytemple.core.error_handler import display_error
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.ui_utils import add_dialog_png_filter, data_dir
from skytemple_files.common.util import add_extension_if_missing
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


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "misc_graphics", "cart_removed.ui"))
class StMiscGraphicsCartRemovedPage(Gtk.Paned):
    __gtype_name__ = "StMiscGraphicsCartRemovedPage"
    module: MiscGraphicsModule
    item_data: str
    button_import: Gtk.ToolButton = cast(Gtk.ToolButton, Gtk.Template.Child())
    export: Gtk.ToolButton = cast(Gtk.ToolButton, Gtk.Template.Child())
    draw_area: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    cart_removed_info: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    table_store: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())

    def __init__(self, module: MiscGraphicsModule, item_data: str):
        super().__init__()
        self.module = module
        self.item_data = item_data
        self.module = module
        self._reinit_image()
        self.draw_area.connect("draw", self.exec_draw)

    @Gtk.Template.Callback()
    def on_cart_removed_info_clicked(self, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _(
                "This is what the game shows when the cartridge is removed while playing.\nIMPORTANT! The game stores this compressed in the ARM9, so this is limited in space.\nIt is recommended to only edit this to change the text color/content."
            ),
            title=_("Cartridge Removed Image Info"),
        )
        md.run()
        md.destroy()

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
            self.module.get_cart_removed_data().save(fn)

    @Gtk.Template.Callback()
    def on_button_import_clicked(self, w: Gtk.MenuToolButton):
        dialog = Gtk.FileChooserNative.new(
            _("Import image as PNG..."),
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
                self.module.set_cart_removed_data(img)
            except Exception as err:
                display_error(sys.exc_info(), str(err), _("Error importing cart removed image."))
            self._reinit_image()

    def _reinit_image(self):
        surface = self.module.get_cart_removed_data()
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
