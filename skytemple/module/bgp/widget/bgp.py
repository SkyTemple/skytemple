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
from skytemple.core.ui_utils import add_dialog_png_filter, data_dir, safe_destroy
from skytemple_files.common.util import add_extension_if_missing
from PIL import Image
from gi.repository import Gtk
from gi.repository.Gtk import ResponseType
from skytemple.controller.main import MainController
from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple_files.common.i18n_util import _

from skytemple.init_locale import LocalePatchedGtkTemplate

if TYPE_CHECKING:
    from skytemple.module.bgp.module import BgpModule  # noqa: W291
INFO_IMEXPORT_ENTIRE = _(
    "- The image is a 256-color indexed PNG.\n- The 256 colors are divided into 16 16 color palettes.\n- Each 8x8 tile in the image MUST only use colors from\n  one of these 16 palettes.\n- The first color in each palette is transparency.\n- Each import must result in a maximum of 1024 unique 8x8 tiles \n  (=not existing with another palette or flipped or rotated)."
)
logger = logging.getLogger(__name__)
import os


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "bgp", "bgp.ui"))
class StBgpBgpPage(Gtk.Box):
    __gtype_name__ = "StBgpBgpPage"
    module: BgpModule
    item_data: int
    dialog_map_import_adjustment: Gtk.Adjustment = cast(Gtk.Adjustment, Gtk.Template.Child())
    dialog_settings_number_collision_adjustment: Gtk.Adjustment = cast(Gtk.Adjustment, Gtk.Template.Child())
    dialog_settings_number_layers_adjustment: Gtk.Adjustment = cast(Gtk.Adjustment, Gtk.Template.Child())
    men_bg_import: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_bg_export: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_tools_tilequant: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    draw_area: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    image1: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    dialog_bg_export: Gtk.Dialog = cast(Gtk.Dialog, Gtk.Template.Child())
    dialog_map_export_btn_close: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    dialog_map_export_btn_ok: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    image6: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image7: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    dialog_bg_import: Gtk.Dialog = cast(Gtk.Dialog, Gtk.Template.Child())
    dialog_map_import_btn_close: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    dialog_map_import_btn_ok: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    bg_import_file: Gtk.FileChooserButton = cast(Gtk.FileChooserButton, Gtk.Template.Child())

    def __init__(self, module: BgpModule, item_data: int):
        super().__init__()
        self.module = module
        self.item_data = item_data
        self.bgp = self.module.get_bgp(self.item_data)
        self._reinit_image()
        self.draw_area.connect("draw", self.exec_draw)

    @Gtk.Template.Callback()
    def on_self_destroy(self, *args):
        # Try to destroy all top-level widgets outside of the template to not leak memory.
        safe_destroy(self.image1)
        safe_destroy(self.dialog_bg_export)
        safe_destroy(self.image6)
        safe_destroy(self.image7)
        safe_destroy(self.dialog_bg_import)

    @Gtk.Template.Callback()
    def on_men_bg_export_activate(self, *args):
        dialog: Gtk.Dialog = self.dialog_bg_export
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())
        resp = dialog.run()
        dialog.hide()
        if resp == ResponseType.OK:
            file_chooser = Gtk.FileChooserNative.new(
                "Export as PNG...",
                MainController.window(),
                Gtk.FileChooserAction.SAVE,
                None,
                None,
            )
            add_dialog_png_filter(file_chooser)
            response = file_chooser.run()
            fn = file_chooser.get_filename()
            file_chooser.destroy()
            if response == Gtk.ResponseType.ACCEPT and fn is not None:
                fn = add_extension_if_missing(fn, "png")
                self.bgp.to_pil().save(fn)

    @Gtk.Template.Callback()
    def on_men_bg_import_activate(self, *args):
        dialog = self.dialog_bg_import
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())
        file_chooser = self.bg_import_file
        resp = dialog.run()
        dialog.hide()
        if resp == ResponseType.OK:
            try:
                path = file_chooser.get_filename()
                if path is not None:
                    with open(path, "rb") as f:
                        self.bgp.from_pil(Image.open(f), True)
            except Exception as err:
                display_error(sys.exc_info(), str(err), _("Error importing the image."))
            self.module.mark_as_modified(self.item_data)
            self._reinit_image()

    @Gtk.Template.Callback()
    def on_format_details_entire_clicked(self, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            INFO_IMEXPORT_ENTIRE,
        )
        md.set_position(Gtk.WindowPosition.CENTER)
        md.run()
        md.destroy()

    @Gtk.Template.Callback()
    def on_converter_tool_clicked(self, *args):
        MainController.show_tilequant_dialog(16, 16)

    @Gtk.Template.Callback()
    def on_men_tools_tilequant_activate(self, *args):
        MainController.show_tilequant_dialog(16, 16)

    def _reinit_image(self):
        self.surface = pil_to_cairo_surface(self.bgp.to_pil().convert("RGBA"))
        self.draw_area.queue_draw()

    def exec_draw(self, wdg, ctx: cairo.Context, *args):
        if self.surface:
            ctx.fill()
            ctx.set_source_surface(self.surface, 0, 0)
            ctx.get_source().set_filter(cairo.Filter.NEAREST)
            ctx.paint()
        return True
